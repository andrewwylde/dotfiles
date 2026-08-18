use std::fs;
use std::path::{Path, PathBuf};

use anyhow::{Context, Result};
use chrono::Utc;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct InstalledPath {
    pub library: PathBuf,
    pub target: String,
    #[serde(rename = "agentPath")]
    pub agent_path: PathBuf,
    pub mode: String,
    #[serde(rename = "createdAt")]
    pub created_at: String,
    pub kind: String,
    pub name: String,
}

impl InstalledPath {
    #[must_use]
    pub fn new(
        library: PathBuf,
        target: impl Into<String>,
        agent_path: PathBuf,
        mode: impl Into<String>,
        kind: impl Into<String>,
        name: impl Into<String>,
    ) -> Self {
        Self {
            library,
            target: target.into(),
            agent_path,
            mode: mode.into(),
            created_at: Utc::now().to_rfc3339(),
            kind: kind.into(),
            name: name.into(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct State {
    pub version: u8,
    pub fanouts: Vec<InstalledPath>,
}

impl Default for State {
    fn default() -> Self {
        Self {
            version: 1,
            fanouts: Vec::new(),
        }
    }
}

impl State {
    pub fn load(path: &Path) -> Result<Self> {
        if !path.exists() {
            return Ok(Self::default());
        }
        let text =
            fs::read_to_string(path).with_context(|| format!("read state {}", path.display()))?;
        let state: Self = serde_json::from_str(&text)
            .with_context(|| format!("parse state {}", path.display()))?;
        Ok(state)
    }

    pub fn write(&self, path: &Path) -> Result<()> {
        let parent = path
            .parent()
            .context("state file has no parent directory")?;
        fs::create_dir_all(parent)
            .with_context(|| format!("create state parent {}", parent.display()))?;
        let temporary = parent.join(format!(
            ".{}.{}.tmp",
            path.file_name()
                .and_then(|name| name.to_str())
                .unwrap_or("agent-sync-state"),
            std::process::id()
        ));
        let mut text = serde_json::to_string_pretty(self)?;
        text.push('\n');
        fs::write(&temporary, text)
            .with_context(|| format!("write temporary state {}", temporary.display()))?;
        fs::rename(&temporary, path)
            .with_context(|| format!("replace state {}", path.display()))?;
        Ok(())
    }

    #[must_use]
    pub fn owns(&self, path: &Path) -> bool {
        self.fanouts.iter().any(|entry| entry.agent_path == path)
    }
}
