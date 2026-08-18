use std::fs;
use std::process::Command;

use tempfile::tempdir;

#[test]
fn sync_installs_symlink_and_copy_with_cursor_overlay() {
    let workspace = tempdir().expect("temporary workspace");
    let dotfiles = workspace.path().join("dotfiles");
    let home = workspace.path().join("home");
    let target_root = workspace.path().join("targets");
    let skill = dotfiles.join("library/skills/demo");

    fs::create_dir_all(&skill).expect("skill directory");
    fs::create_dir_all(&home).expect("home directory");
    fs::write(
        skill.join("SKILL.md"),
        "---\nname: demo\ndescription: shared\nmetadata:\n  source: public\n---\n\n# Demo\n",
    )
    .expect("skill body");
    fs::write(
        skill.join("manifest.toml"),
        r#"
[overlays.cursor]
body_append = """

cursor only
"""

[overlays.cursor.frontmatter]
disable-model-invocation = true

[overlays.cursor.frontmatter.metadata]
source = "cursor"
"#,
    )
    .expect("manifest");

    let output = Command::new(env!("CARGO_BIN_EXE_agent-sync"))
        .args(["sync", "--root"])
        .arg(&target_root)
        .env("DOTFILES_DIR", &dotfiles)
        .env("HOME", &home)
        .output()
        .expect("run agent-sync");

    assert!(
        output.status.success(),
        "sync failed:\nstdout: {}\nstderr: {}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );

    let claude = target_root.join(".claude/skills/andrew-demo");
    let cursor = target_root.join(".cursor/skills/andrew-demo");
    assert!(
        fs::symlink_metadata(&claude)
            .expect("claude install")
            .file_type()
            .is_symlink(),
        "Claude install should be a symlink"
    );
    assert!(
        fs::metadata(&cursor).expect("cursor install").is_dir(),
        "Cursor install should be a directory copy"
    );
    assert!(
        !fs::symlink_metadata(&cursor)
            .expect("cursor install")
            .file_type()
            .is_symlink(),
        "Cursor install must not be a symlink"
    );

    let cursor_body = fs::read_to_string(cursor.join("SKILL.md")).expect("Cursor wrapper contents");
    assert!(cursor_body.contains("disable-model-invocation: true"));
    assert!(cursor_body.contains("source: cursor"));
    assert!(cursor_body.contains("cursor only"));
}

#[test]
fn sync_merges_hook_packs_without_clobbering_handwritten_entries() {
    let workspace = tempdir().expect("temporary workspace");
    let dotfiles = workspace.path().join("dotfiles");
    let home = workspace.path().join("home");
    let target_root = workspace.path().join("targets");
    let pack = dotfiles.join("library/hooks/guards");
    fs::create_dir_all(&pack).expect("Hook pack directory");
    fs::create_dir_all(target_root.join(".cursor")).expect("Cursor target");
    fs::create_dir_all(target_root.join(".claude")).expect("Claude target");
    fs::create_dir_all(&home).expect("home directory");
    fs::write(pack.join("guard.sh"), "#!/bin/sh\nexit 0\n").expect("hook script");
    fs::write(
        pack.join("manifest.toml"),
        r#"
version = "2.1.0"
exclude = ["opencode", "pi"]

[hooks.cursor]
beforeShellExecution = [{ command = "./guard.sh", timeout = 5 }]

[hooks.claude]
PreToolUse = [{ matcher = "Bash", hooks = [{ type = "command", command = "./guard.sh" }] }]
"#,
    )
    .expect("Hook pack Manifest");
    fs::write(
        target_root.join(".cursor/hooks.json"),
        r#"{"version":1,"hooks":{"beforeShellExecution":[{"command":"manual.sh"}]}}"#,
    )
    .expect("Cursor config");
    fs::write(
        target_root.join(".claude/settings.json"),
        r#"{"model":"opus","hooks":{"PreToolUse":[{"matcher":"Read","hooks":[]}]}}"#,
    )
    .expect("Claude config");

    let output = Command::new(env!("CARGO_BIN_EXE_agent-sync"))
        .args(["sync", "--root"])
        .arg(&target_root)
        .env("DOTFILES_DIR", &dotfiles)
        .env("HOME", &home)
        .output()
        .expect("run agent-sync");
    assert!(
        output.status.success(),
        "sync failed:\n{}",
        String::from_utf8_lossy(&output.stderr)
    );

    let cursor_config: serde_json::Value = serde_json::from_str(
        &fs::read_to_string(target_root.join(".cursor/hooks.json")).expect("Cursor hooks"),
    )
    .expect("valid Cursor hooks");
    let cursor_entries = cursor_config["hooks"]["beforeShellExecution"]
        .as_array()
        .expect("Cursor event array");
    assert_eq!(cursor_entries[0]["command"], "manual.sh");
    assert_eq!(
        cursor_entries[1]["_as"],
        "agent-sync:guards:2.1.0:beforeShellExecution:0"
    );
    assert!(cursor_entries[1]["command"]
        .as_str()
        .expect("rewritten command")
        .ends_with(".cursor/hooks/as-guards-guard.sh"));
    assert!(
        !fs::symlink_metadata(target_root.join(".cursor/hooks/as-guards-guard.sh"))
            .expect("Cursor hook script")
            .file_type()
            .is_symlink()
    );

    let claude_config: serde_json::Value = serde_json::from_str(
        &fs::read_to_string(target_root.join(".claude/settings.json")).expect("Claude settings"),
    )
    .expect("valid Claude settings");
    assert_eq!(claude_config["model"], "opus");
    assert_eq!(
        claude_config["hooks"]["PreToolUse"][1]["_as"],
        "agent-sync:guards:2.1.0:PreToolUse:0"
    );
    assert!(
        fs::symlink_metadata(target_root.join(".claude/hooks/as-guards-guard.sh"))
            .expect("Claude hook script")
            .file_type()
            .is_symlink()
    );

    let verify = Command::new(env!("CARGO_BIN_EXE_agent-sync"))
        .args(["verify", "--root"])
        .arg(&target_root)
        .env("DOTFILES_DIR", &dotfiles)
        .env("HOME", &home)
        .output()
        .expect("run verify");
    assert!(
        verify.status.success(),
        "verify failed:\nstdout: {}\nstderr: {}",
        String::from_utf8_lossy(&verify.stdout),
        String::from_utf8_lossy(&verify.stderr)
    );
}

#[test]
fn local_tombstone_suppresses_public_item() {
    let workspace = tempdir().expect("temporary workspace");
    let dotfiles = workspace.path().join("dotfiles");
    let home = workspace.path().join("home");
    let target_root = workspace.path().join("targets");
    let public = dotfiles.join("library/skills/hidden");
    let tombstone = home.join("dotfiles-local/library/skills/hidden");
    fs::create_dir_all(&public).expect("public skill");
    fs::create_dir_all(&tombstone).expect("local tombstone");
    fs::write(public.join("SKILL.md"), "# Hidden\n").expect("public body");
    fs::write(tombstone.join(".agent-sync-tombstone"), "").expect("tombstone marker");

    let output = Command::new(env!("CARGO_BIN_EXE_agent-sync"))
        .args(["sync", "--root"])
        .arg(&target_root)
        .env("DOTFILES_DIR", &dotfiles)
        .env("HOME", &home)
        .output()
        .expect("run agent-sync");
    assert!(output.status.success());
    assert!(!target_root.join(".claude/skills/andrew-hidden").exists());
    assert!(!target_root.join(".cursor/skills/andrew-hidden").exists());
}
