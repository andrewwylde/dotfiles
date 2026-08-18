use std::env;
use std::path::{Path, PathBuf};

use anyhow::{bail, Context, Result};

#[derive(Debug, Clone)]
pub struct Config {
    pub dotfiles_dir: PathBuf,
    pub public_library: PathBuf,
    pub local_library: PathBuf,
    pub home: PathBuf,
    pub target_home: PathBuf,
    pub owner_prefix: String,
    pub state_file: PathBuf,
    pub wrapper_root: PathBuf,
    pub backup_root: PathBuf,
}

impl Config {
    pub fn discover(root: Option<PathBuf>) -> Result<Self> {
        let home = env::var_os("HOME")
            .map(PathBuf::from)
            .context("HOME is not set")?;
        let dotfiles_dir = if let Some(value) = env::var_os("DOTFILES_DIR") {
            PathBuf::from(value)
        } else {
            detect_dotfiles_dir(&home)?
        };

        if !dotfiles_dir.is_dir() {
            bail!(
                "dotfiles directory does not exist: {}",
                dotfiles_dir.display()
            );
        }

        let owner_prefix =
            env::var("AGENT_SYNC_OWNER_PREFIX").unwrap_or_else(|_| "andrew".to_owned());
        if owner_prefix.is_empty()
            || !owner_prefix
                .chars()
                .all(|character| character.is_ascii_alphanumeric() || character == '-')
        {
            bail!("owner_prefix must contain only ASCII letters, numbers, and hyphens");
        }

        Ok(Self {
            public_library: dotfiles_dir.join("library"),
            local_library: home.join("dotfiles-local/library"),
            target_home: root.unwrap_or_else(|| home.clone()),
            state_file: home.join(".agent-sync-state.json"),
            wrapper_root: home.join(".agent-sync/wrappers"),
            backup_root: dotfiles_dir.join(".agent-sync-backups"),
            dotfiles_dir,
            home,
            owner_prefix,
        })
    }

    #[must_use]
    pub fn fanout_name(&self, name: &str, vendor_origin: Option<&str>) -> String {
        vendor_origin.map_or_else(
            || format!("{}-{name}", self.owner_prefix),
            |origin| format!("vendor-{origin}-{name}"),
        )
    }
}

fn detect_dotfiles_dir(home: &Path) -> Result<PathBuf> {
    let public = home.join("dotfiles");
    if public.is_dir() {
        return Ok(public);
    }

    let local = home.join("dotfiles-local");
    if local.is_dir() {
        return Ok(local);
    }

    bail!("could not find ~/dotfiles or ~/dotfiles-local; set DOTFILES_DIR explicitly")
}
