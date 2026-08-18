use std::fs;
use std::process::Command;

use tempfile::tempdir;

#[test]
fn migrate_write_backs_up_moves_syncs_and_rolls_back() {
    let workspace = tempdir().expect("temporary workspace");
    let dotfiles = workspace.path().join("dotfiles");
    let home = workspace.path().join("home");
    let target_root = workspace.path().join("targets");
    let legacy = dotfiles.join(".claude/commands/hello.md");
    fs::create_dir_all(legacy.parent().expect("legacy parent")).expect("legacy tree");
    fs::create_dir_all(&home).expect("home");
    fs::write(&legacy, "# Hello\n").expect("legacy command");

    let bare = run(&dotfiles, &home, &target_root, &["migrate"]);
    assert!(!bare.status.success(), "bare migrate must refuse");

    let write = run(
        &dotfiles,
        &home,
        &target_root,
        &["migrate", "--write", "--allow-dirty"],
    );
    assert!(
        write.status.success(),
        "migrate failed:\nstdout: {}\nstderr: {}",
        String::from_utf8_lossy(&write.stdout),
        String::from_utf8_lossy(&write.stderr)
    );
    assert!(!legacy.exists(), "legacy source should be retired");
    assert_eq!(
        fs::read_to_string(dotfiles.join("library/commands/hello/COMMAND.md"))
            .expect("migrated command"),
        "# Hello\n"
    );
    assert!(target_root
        .join(".claude/commands/andrew-hello.md")
        .exists());
    assert!(target_root
        .join(".cursor/skills/andrew-hello/SKILL.md")
        .exists());

    let stdout = String::from_utf8(write.stdout).expect("UTF-8 migrate output");
    let backup_id = stdout
        .lines()
        .find_map(|line| line.strip_prefix("BACKUP "))
        .expect("backup id in output");
    assert!(dotfiles
        .join(".agent-sync-backups")
        .join(backup_id)
        .join("backup.json")
        .is_file());

    let rollback = run(
        &dotfiles,
        &home,
        &target_root,
        &["migrate", "--rollback", backup_id],
    );
    assert!(
        rollback.status.success(),
        "rollback failed:\n{}",
        String::from_utf8_lossy(&rollback.stderr)
    );
    assert_eq!(
        fs::read_to_string(&legacy).expect("restored legacy command"),
        "# Hello\n"
    );
    assert!(!dotfiles.join("library/commands/hello").exists());
    assert!(!target_root
        .join(".claude/commands/andrew-hello.md")
        .exists());
}

fn run(
    dotfiles: &std::path::Path,
    home: &std::path::Path,
    target_root: &std::path::Path,
    args: &[&str],
) -> std::process::Output {
    let mut command = Command::new(env!("CARGO_BIN_EXE_agent-sync"));
    command
        .args(args)
        .arg("--root")
        .arg(target_root)
        .env("DOTFILES_DIR", dotfiles)
        .env("HOME", home);
    command.output().expect("run agent-sync")
}
