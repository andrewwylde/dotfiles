use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

use anyhow::{bail, Context, Result};
use chrono::Utc;
use regex::Regex;
use serde::{Deserialize, Serialize};
use walkdir::WalkDir;

use crate::cli::MigrateArgs;
use crate::config::Config;
use crate::install;
use crate::library::Kind;
use crate::{sync, verify};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Disposition {
    Library,
    Vendor,
    Private,
    Abandon,
}

impl Disposition {
    const fn label(self) -> &'static str {
        match self {
            Self::Library => "LIBRARY",
            Self::Vendor => "VENDOR",
            Self::Private => "PRIVATE",
            Self::Abandon => "ABANDON",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Materialization {
    Normal,
    HookPack,
}

#[derive(Debug, Clone)]
struct MigrationAction {
    source: PathBuf,
    destination: Option<PathBuf>,
    disposition: Disposition,
    kind: Kind,
    name: String,
    note: String,
    materialization: Materialization,
}

#[derive(Debug, Serialize, Deserialize)]
struct BackupManifest {
    id: String,
    created_at: String,
    target_snapshot: bool,
    records: Vec<BackupRecord>,
}

#[derive(Debug, Serialize, Deserialize)]
struct BackupRecord {
    original: PathBuf,
    backup: PathBuf,
    existed: bool,
    layer: String,
}

pub fn run(config: &Config, args: &MigrateArgs) -> Result<()> {
    if let Some(id) = &args.rollback {
        return rollback(config, id);
    }
    if args.dry_run == args.write {
        bail!("migrate requires exactly one of --dry-run or --write");
    }

    let inventory = args
        .inventory
        .as_deref()
        .map(parse_inventory)
        .transpose()?
        .unwrap_or_default();
    let actions = scan_actions(config, &inventory)?;
    print_plan(config, &actions);
    if args.dry_run {
        println!(
            "DRY-RUN complete: {} actions; no files were changed",
            actions.len()
        );
        return Ok(());
    }

    preflight(config, &actions, args.allow_dirty)?;
    let backup = create_backup(config, &actions, args.backup_targets)?;
    println!("BACKUP {}", backup.id);

    for action in &actions {
        apply_action(action)?;
    }
    sync::run(config, false).context("fan-out after migrate failed")?;
    if !verify::run(config).context("post-migrate verify failed")? {
        bail!(
            "post-migrate verification failed; restore with `agent-sync migrate --rollback {}`",
            backup.id
        );
    }
    println!("MIGRATE complete; rollback id {}", backup.id);
    Ok(())
}

fn scan_actions(
    config: &Config,
    inventory: &BTreeMap<PathBuf, Disposition>,
) -> Result<Vec<MigrationAction>> {
    let mut actions = Vec::new();
    scan_target_kind(config, ".claude", Kind::Skills, inventory, &mut actions)?;
    scan_target_kind(config, ".claude", Kind::Commands, inventory, &mut actions)?;
    scan_target_kind(config, ".claude", Kind::Agents, inventory, &mut actions)?;
    scan_target_kind(config, ".cursor", Kind::Skills, inventory, &mut actions)?;
    scan_target_kind(config, ".cursor", Kind::Commands, inventory, &mut actions)?;
    scan_target_kind(config, ".cursor", Kind::Agents, inventory, &mut actions)?;

    let cursor_products = config.dotfiles_dir.join(".cursor/skills-cursor");
    if install::path_exists(&cursor_products) {
        actions.push(MigrationAction {
            source: cursor_products,
            destination: None,
            disposition: Disposition::Abandon,
            kind: Kind::Skills,
            name: "skills-cursor".to_owned(),
            note: "Cursor-managed product tree".to_owned(),
            materialization: Materialization::Normal,
        });
    }

    deduplicate(&mut actions)?;
    actions.sort_by(|left, right| left.source.cmp(&right.source));
    Ok(actions)
}

fn scan_target_kind(
    config: &Config,
    target_dir: &str,
    kind: Kind,
    inventory: &BTreeMap<PathBuf, Disposition>,
    actions: &mut Vec<MigrationAction>,
) -> Result<()> {
    let relative_root = Path::new(target_dir).join(kind.dir_name());
    let root = config.dotfiles_dir.join(&relative_root);
    if !root.is_dir() {
        return Ok(());
    }
    let mut entries = fs::read_dir(&root)
        .with_context(|| format!("read legacy tree {}", root.display()))?
        .collect::<std::io::Result<Vec<_>>>()?;
    entries.sort_by_key(fs::DirEntry::file_name);

    for entry in entries {
        let source = entry.path();
        let relative = relative_root.join(entry.file_name());
        if target_dir == ".cursor" && kind == Kind::Skills && entry.file_name() == "_shared" {
            let disposition = inventory
                .get(&relative)
                .copied()
                .unwrap_or(Disposition::Library);
            actions.push(MigrationAction {
                source,
                destination: (disposition == Disposition::Library)
                    .then(|| config.public_library.join("hooks/skill-gates")),
                disposition,
                kind: Kind::Hooks,
                name: "skill-gates".to_owned(),
                note: "Cursor shared hooks plus skill_gate.py".to_owned(),
                materialization: Materialization::HookPack,
            });
            continue;
        }
        if target_dir == ".claude" && kind == Kind::Skills && entry.file_name() == "_shared" {
            scan_claude_shared(config, &source, inventory, actions)?;
            continue;
        }

        let name = source
            .file_stem()
            .and_then(|name| name.to_str())
            .unwrap_or_default()
            .to_owned();
        if name.is_empty() {
            continue;
        }
        let classified = classify_source(&source, kind)?;
        let disposition = inventory.get(&relative).copied().unwrap_or(classified);
        let destination = destination_for(config, kind, &name, disposition, &relative);
        actions.push(MigrationAction {
            source,
            destination,
            disposition,
            kind,
            name,
            note: if inventory.contains_key(&relative) {
                "inventory disposition".to_owned()
            } else {
                "live scan classification".to_owned()
            },
            materialization: Materialization::Normal,
        });
    }
    Ok(())
}

fn scan_claude_shared(
    config: &Config,
    source: &Path,
    inventory: &BTreeMap<PathBuf, Disposition>,
    actions: &mut Vec<MigrationAction>,
) -> Result<()> {
    if !source.is_dir() {
        return Ok(());
    }
    for entry in fs::read_dir(source)? {
        let entry = entry?;
        let path = entry.path();
        if path.extension().and_then(|extension| extension.to_str()) != Some("md") {
            continue;
        }
        let name = path
            .file_stem()
            .and_then(|value| value.to_str())
            .context("shared Markdown file has no UTF-8 stem")?
            .to_owned();
        let relative = path.strip_prefix(&config.dotfiles_dir)?.to_path_buf();
        let disposition = inventory
            .get(Path::new(".claude/skills/_shared"))
            .copied()
            .unwrap_or(Disposition::Library);
        actions.push(MigrationAction {
            source: path,
            destination: (disposition == Disposition::Library)
                .then(|| config.public_library.join("skills").join(&name)),
            disposition,
            kind: Kind::Skills,
            name,
            note: format!("split shared Markdown {}", relative.display()),
            materialization: Materialization::Normal,
        });
    }
    Ok(())
}

fn classify_source(source: &Path, kind: Kind) -> Result<Disposition> {
    let metadata = fs::symlink_metadata(source)
        .with_context(|| format!("inspect legacy item {}", source.display()))?;
    if metadata.file_type().is_symlink() {
        return Ok(if source.exists() {
            Disposition::Library
        } else {
            Disposition::Abandon
        });
    }
    if metadata.is_file() {
        return Ok(
            if source.extension().and_then(|extension| extension.to_str()) == Some("md") {
                Disposition::Library
            } else {
                Disposition::Abandon
            },
        );
    }
    if !metadata.is_dir() {
        return Ok(Disposition::Abandon);
    }
    let expected = kind.source_file().unwrap_or("manifest.toml");
    if source.join(expected).is_file() || contains_markdown(source)? {
        Ok(Disposition::Library)
    } else {
        Ok(Disposition::Abandon)
    }
}

fn contains_markdown(source: &Path) -> Result<bool> {
    for entry in WalkDir::new(source).max_depth(2) {
        let entry = entry?;
        if entry.file_type().is_file()
            && entry.path().extension().and_then(|value| value.to_str()) == Some("md")
        {
            return Ok(true);
        }
    }
    Ok(false)
}

fn destination_for(
    config: &Config,
    kind: Kind,
    name: &str,
    disposition: Disposition,
    relative: &Path,
) -> Option<PathBuf> {
    if !matches!(disposition, Disposition::Library | Disposition::Vendor) {
        return None;
    }
    let vendor =
        disposition == Disposition::Vendor || relative.starts_with(".cursor/skills-cursor");
    Some(if vendor {
        config
            .public_library
            .join("skills/vendor/cursor")
            .join(name)
    } else {
        config.public_library.join(kind.dir_name()).join(name)
    })
}

fn deduplicate(actions: &mut [MigrationAction]) -> Result<()> {
    let mut destinations: BTreeMap<PathBuf, Vec<usize>> = BTreeMap::new();
    for (index, action) in actions.iter().enumerate() {
        if matches!(
            action.disposition,
            Disposition::Library | Disposition::Vendor
        ) {
            if let Some(destination) = &action.destination {
                destinations
                    .entry(destination.clone())
                    .or_default()
                    .push(index);
            }
        }
    }
    for indexes in destinations.into_values().filter(|group| group.len() > 1) {
        let winner = indexes
            .iter()
            .copied()
            .min_by_key(|index| usize::from(!is_claude_path(&actions[*index].source)))
            .unwrap_or(indexes[0]);
        for index in indexes {
            if index == winner {
                continue;
            }
            let identical = same_content(&actions[winner].source, &actions[index].source)?;
            actions[index].disposition = Disposition::Abandon;
            actions[index].destination = None;
            actions[index].note = if identical {
                "duplicate content; prefer Claude".to_owned()
            } else {
                "same-name conflict; prefer Claude and retire Target copy".to_owned()
            };
        }
    }
    Ok(())
}

fn is_claude_path(path: &Path) -> bool {
    path.components()
        .any(|component| component.as_os_str() == ".claude")
}

fn same_content(left: &Path, right: &Path) -> Result<bool> {
    if left.is_file() && right.is_file() {
        return Ok(fs::read(left)? == fs::read(right)?);
    }
    if left.is_dir() && right.is_dir() {
        let left_files = relative_files(left)?;
        let right_files = relative_files(right)?;
        if left_files.keys().collect::<Vec<_>>() != right_files.keys().collect::<Vec<_>>() {
            return Ok(false);
        }
        for (relative, left_path) in left_files {
            if fs::read(left_path)? != fs::read(&right_files[&relative])? {
                return Ok(false);
            }
        }
        return Ok(true);
    }
    Ok(false)
}

fn relative_files(root: &Path) -> Result<BTreeMap<PathBuf, PathBuf>> {
    let mut files = BTreeMap::new();
    for entry in WalkDir::new(root).follow_links(true) {
        let entry = entry?;
        if entry.file_type().is_file() {
            files.insert(
                entry.path().strip_prefix(root)?.to_path_buf(),
                entry.path().to_path_buf(),
            );
        }
    }
    Ok(files)
}

fn parse_inventory(path: &Path) -> Result<BTreeMap<PathBuf, Disposition>> {
    let text =
        fs::read_to_string(path).with_context(|| format!("read inventory {}", path.display()))?;
    let quoted_path = Regex::new(r"`((?:\.claude|\.cursor)/[^`]+)`")?;
    let mut inventory = BTreeMap::new();
    for line in text
        .lines()
        .filter(|line| line.trim_start().starts_with('|'))
    {
        let Some(path_capture) = quoted_path.captures(line) else {
            continue;
        };
        let source = PathBuf::from(&path_capture[1]);
        let lower = line.to_ascii_lowercase();
        let disposition = if lower.contains("| library |") {
            Some(Disposition::Library)
        } else if lower.contains("| gitignore-private |") || lower.contains("| machine-local |") {
            Some(Disposition::Private)
        } else if lower.contains("| abandon |") {
            Some(Disposition::Abandon)
        } else if lower.contains("| vendor/cursor |") {
            Some(Disposition::Vendor)
        } else {
            None
        };
        if let Some(disposition) = disposition {
            inventory.insert(source, disposition);
        }
    }
    Ok(inventory)
}

fn print_plan(config: &Config, actions: &[MigrationAction]) {
    println!("disposition\tkind\tsource_path\tdest_path\taction\tnotes");
    for action in actions {
        let source = action
            .source
            .strip_prefix(&config.dotfiles_dir)
            .unwrap_or(&action.source);
        let destination = action
            .destination
            .as_ref()
            .map_or_else(|| "-".to_owned(), |path| path.display().to_string());
        println!(
            "{}\t{}\t{}\t{}\t{}\t{}",
            action.disposition.label(),
            action.kind,
            source.display(),
            destination,
            match action.disposition {
                Disposition::Library => "move-to-library",
                Disposition::Vendor => "move-to-vendor-library",
                Disposition::Private => "leave-private",
                Disposition::Abandon => "remove-legacy",
            },
            format!("{} [{}]", action.note, action.name)
        );
    }
}

fn preflight(config: &Config, actions: &[MigrationAction], allow_dirty: bool) -> Result<()> {
    if !allow_dirty {
        let output = Command::new("git")
            .args(["status", "--porcelain", "--", ".claude", ".cursor"])
            .current_dir(&config.dotfiles_dir)
            .output()
            .context("run git status preflight")?;
        if !output.status.success() {
            bail!("git status preflight failed");
        }
        if !output.stdout.is_empty() {
            bail!(
                "legacy Target trees are dirty; review changes and pass --allow-dirty to migrate the working tree"
            );
        }
    }
    for action in actions {
        if !matches!(
            action.disposition,
            Disposition::Library | Disposition::Vendor
        ) {
            continue;
        }
        let destination = action
            .destination
            .as_ref()
            .context("Library action missing destination")?;
        if install::path_exists(destination) {
            bail!(
                "Library destination already exists: {}; rollback or resolve the conflict first",
                destination.display()
            );
        }
    }
    Ok(())
}

fn create_backup(
    config: &Config,
    actions: &[MigrationAction],
    backup_targets: bool,
) -> Result<BackupManifest> {
    let id = Utc::now().format("%Y%m%dT%H%M%S%.3fZ").to_string();
    let root = config.backup_root.join(&id);
    fs::create_dir_all(&root).with_context(|| format!("create backup {}", root.display()))?;
    let mut records = Vec::new();
    let mut seen = BTreeSet::new();

    for action in actions {
        add_backup_record(
            &root,
            &config.dotfiles_dir,
            &action.source,
            "repo",
            &mut seen,
            &mut records,
        )?;
        if let Some(destination) = &action.destination {
            add_backup_record(
                &root,
                &config.dotfiles_dir,
                destination,
                "repo",
                &mut seen,
                &mut records,
            )?;
        }
    }
    add_backup_record(
        &root,
        &config.home,
        &config.state_file,
        "state",
        &mut seen,
        &mut records,
    )?;
    if backup_targets {
        for path in target_snapshot_paths(config) {
            add_backup_record(
                &root,
                &config.target_home,
                &path,
                "target",
                &mut seen,
                &mut records,
            )?;
        }
    }

    let manifest = BackupManifest {
        id,
        created_at: Utc::now().to_rfc3339(),
        target_snapshot: backup_targets,
        records,
    };
    let text = serde_json::to_string_pretty(&manifest)?;
    fs::write(root.join("backup.json"), format!("{text}\n"))?;
    Ok(manifest)
}

fn add_backup_record(
    backup_root: &Path,
    base: &Path,
    original: &Path,
    layer: &str,
    seen: &mut BTreeSet<PathBuf>,
    records: &mut Vec<BackupRecord>,
) -> Result<()> {
    if !seen.insert(original.to_path_buf()) {
        return Ok(());
    }
    let relative = original.strip_prefix(base).with_context(|| {
        format!(
            "backup path {} is outside expected base {}",
            original.display(),
            base.display()
        )
    })?;
    let backup = backup_root.join("files").join(layer).join(relative);
    let existed = install::path_exists(original);
    if existed {
        copy_preserving_symlink(original, &backup)?;
    }
    records.push(BackupRecord {
        original: original.to_path_buf(),
        backup,
        existed,
        layer: layer.to_owned(),
    });
    Ok(())
}

fn target_snapshot_paths(config: &Config) -> Vec<PathBuf> {
    [
        ".claude/skills",
        ".claude/commands",
        ".claude/agents",
        ".claude/hooks",
        ".claude/settings.json",
        ".cursor/skills",
        ".cursor/agents",
        ".cursor/hooks",
        ".cursor/hooks.json",
        ".config/opencode/skills",
        ".config/opencode/commands",
        ".config/opencode/agents",
        ".pi/agent/skills",
    ]
    .into_iter()
    .map(|relative| config.target_home.join(relative))
    .collect()
}

fn apply_action(action: &MigrationAction) -> Result<()> {
    match action.disposition {
        Disposition::Private => Ok(()),
        Disposition::Abandon => install::remove_path(&action.source),
        Disposition::Library | Disposition::Vendor => {
            let destination = action
                .destination
                .as_ref()
                .context("Library action missing destination")?;
            match action.materialization {
                Materialization::Normal => {
                    materialize_normal(action, destination)?;
                }
                Materialization::HookPack => {
                    materialize_hook_pack(&action.source, destination)?;
                }
            }
            install::remove_path(&action.source)
        }
    }
}

fn materialize_normal(action: &MigrationAction, destination: &Path) -> Result<()> {
    let metadata = fs::metadata(&action.source)
        .with_context(|| format!("read migration source {}", action.source.display()))?;
    if metadata.is_dir() {
        install::copy_path(&action.source, destination)?;
        let expected = action
            .kind
            .source_file()
            .context("normal Hook packs are not supported")?;
        if !destination.join(expected).is_file() {
            let markdown = first_markdown(destination)?.with_context(|| {
                format!(
                    "cannot classify {}: no Markdown body",
                    action.source.display()
                )
            })?;
            fs::copy(&markdown, destination.join(expected))?;
            if markdown != destination.join(expected) {
                install::remove_path(&markdown)?;
            }
        }
    } else {
        fs::create_dir_all(destination)?;
        let expected = action
            .kind
            .source_file()
            .context("normal Hook packs are not supported")?;
        fs::copy(&action.source, destination.join(expected))?;
    }
    Ok(())
}

fn first_markdown(root: &Path) -> Result<Option<PathBuf>> {
    let mut files = WalkDir::new(root)
        .max_depth(2)
        .into_iter()
        .collect::<std::result::Result<Vec<_>, _>>()?;
    files.sort_by_key(|entry| entry.path().to_path_buf());
    Ok(files
        .into_iter()
        .map(|entry| entry.into_path())
        .find(|path| {
            path.is_file()
                && path.extension().and_then(|extension| extension.to_str()) == Some("md")
        }))
}

fn materialize_hook_pack(source: &Path, destination: &Path) -> Result<()> {
    fs::create_dir_all(destination)?;
    let scripts = source.join("hooks");
    if scripts.is_dir() {
        for entry in fs::read_dir(&scripts)? {
            let entry = entry?;
            if entry.path().is_file() {
                install::copy_path(&entry.path(), &destination.join(entry.file_name()))?;
            }
        }
    }
    let gate = source.join("skill_gate.py");
    if gate.is_file() {
        install::copy_path(&gate, &destination.join("skill_gate.py"))?;
    }
    let enforce = destination.join("enforce-gate.sh");
    if enforce.is_file() {
        let body = fs::read_to_string(&enforce)?;
        fs::write(
            &enforce,
            body.replace(
                "${HOME}/.cursor/skills/_shared/skill_gate.py",
                "${HOME}/.cursor/hooks/as-skill-gates-skill_gate.py",
            ),
        )?;
    }
    fs::write(destination.join("manifest.toml"), generated_hook_manifest())?;
    Ok(())
}

fn generated_hook_manifest() -> &'static str {
    r#"version = "1.0.0"
exclude = ["claude", "opencode", "pi"]

[hooks.cursor]
beforeShellExecution = [
  { command = "./block-worktree-remove.sh", matcher = "worktree\\s+(remove|rm)\\b|(?:^|[\\s;|&])(?:/bin/)?rm(?:\\s|$)", failClosed = true, timeout = 10 },
  { command = "./block-root-writes.sh", failClosed = true, timeout = 10 },
  { command = "./block-pr-diff-artifacts.sh", failClosed = true, timeout = 10 },
]
preToolUse = [
  { command = "./enforce-gate.sh", matcher = "StrReplace|Write|EditNotebook|ApplyPatch", failClosed = true, timeout = 10 },
  { command = "./guard-markdown-artifacts.sh", matcher = "StrReplace|Write|EditNotebook|ApplyPatch", failClosed = true, timeout = 10 },
]
"#
}

fn rollback(config: &Config, id: &str) -> Result<()> {
    let valid_id = Regex::new(r"^[A-Za-z0-9._-]+$")?;
    if !valid_id.is_match(id) {
        bail!("invalid rollback id");
    }
    let backup_root = config.backup_root.join(id);
    let manifest_path = backup_root.join("backup.json");
    let text = fs::read_to_string(&manifest_path)
        .with_context(|| format!("read backup {}", manifest_path.display()))?;
    let manifest: BackupManifest = serde_json::from_str(&text)
        .with_context(|| format!("parse backup {}", manifest_path.display()))?;

    remove_new_fanouts(config, &manifest)?;
    for record in &manifest.records {
        install::remove_path(&record.original)?;
    }
    for record in &manifest.records {
        if record.existed {
            copy_preserving_symlink(&record.backup, &record.original)?;
        }
    }
    if !manifest.target_snapshot {
        crate::hooks::remove_managed(config)?;
    }
    println!("ROLLBACK {} restored", manifest.id);
    Ok(())
}

fn remove_new_fanouts(config: &Config, manifest: &BackupManifest) -> Result<()> {
    let previous_state_record = manifest
        .records
        .iter()
        .find(|record| record.layer == "state");
    let previous_paths = if let Some(record) = previous_state_record.filter(|record| record.existed)
    {
        let text = fs::read_to_string(&record.backup)?;
        let state: crate::state::State = serde_json::from_str(&text)?;
        state
            .fanouts
            .into_iter()
            .map(|entry| entry.agent_path)
            .collect::<BTreeSet<_>>()
    } else {
        BTreeSet::new()
    };
    let current = crate::state::State::load(&config.state_file)?;
    for entry in current
        .fanouts
        .into_iter()
        .filter(|entry| !previous_paths.contains(&entry.agent_path))
    {
        if !install::is_npx_owned_symlink(&entry.agent_path)? {
            install::remove_path(&entry.agent_path)?;
        }
    }
    Ok(())
}

fn copy_preserving_symlink(source: &Path, destination: &Path) -> Result<()> {
    let metadata = fs::symlink_metadata(source)?;
    if metadata.file_type().is_symlink() {
        if let Some(parent) = destination.parent() {
            fs::create_dir_all(parent)?;
        }
        let target = fs::read_link(source)?;
        create_symlink(&target, destination)?;
        Ok(())
    } else if metadata.is_dir() {
        fs::create_dir_all(destination)?;
        fs::set_permissions(destination, metadata.permissions())?;
        let mut entries = fs::read_dir(source)?.collect::<std::io::Result<Vec<_>>>()?;
        entries.sort_by_key(fs::DirEntry::file_name);
        for entry in entries {
            copy_preserving_symlink(
                &entry.path(),
                &destination.join(entry.file_name()),
            )?;
        }
        Ok(())
    } else {
        install::copy_path(source, destination)
    }
}

#[cfg(unix)]
fn create_symlink(target: &Path, destination: &Path) -> Result<()> {
    std::os::unix::fs::symlink(target, destination)?;
    Ok(())
}

#[cfg(windows)]
fn create_symlink(target: &Path, destination: &Path) -> Result<()> {
    if target.is_dir() {
        std::os::windows::fs::symlink_dir(target, destination)?;
    } else {
        std::os::windows::fs::symlink_file(target, destination)?;
    }
    Ok(())
}
