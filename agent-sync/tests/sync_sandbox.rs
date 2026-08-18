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
