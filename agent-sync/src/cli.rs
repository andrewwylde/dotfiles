use std::path::PathBuf;

use clap::{Args, Parser, Subcommand};

#[derive(Debug, Parser)]
#[command(name = "agent-sync", version, about)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Command,
}

#[derive(Debug, Subcommand)]
pub enum Command {
    /// Fan out the effective Library to every supported Target.
    Sync(SyncArgs),
    /// Check installed Target files against the effective Library.
    Verify(RootArgs),
    /// Show effective, shadowed, and tombstoned Library items.
    List(RootArgs),
    /// Move legacy per-Target trees into the Library.
    Migrate(MigrateArgs),
}

#[derive(Debug, Args)]
pub struct SyncArgs {
    /// Print the fan-out plan without writing anything.
    #[arg(long)]
    pub dry_run: bool,

    /// Override the Target home base (for sandboxes and tests).
    #[arg(long, value_name = "SANDBOX")]
    pub root: Option<PathBuf>,
}

#[derive(Debug, Args)]
pub struct RootArgs {
    /// Override the Target home base (for sandboxes and tests).
    #[arg(long, value_name = "SANDBOX")]
    pub root: Option<PathBuf>,
}

#[derive(Debug, Args)]
pub struct MigrateArgs {
    /// Print the migration plan without mutating files.
    #[arg(long, conflicts_with_all = ["write", "rollback"])]
    pub dry_run: bool,

    /// Apply the migration, back it up, fan out, and verify.
    #[arg(long, conflicts_with_all = ["dry_run", "rollback"])]
    pub write: bool,

    /// Include supported Target directories in the migration backup.
    #[arg(long, requires = "write")]
    pub backup_targets: bool,

    /// Permit tracked or untracked changes under legacy Target trees.
    #[arg(long, requires = "write")]
    pub allow_dirty: bool,

    /// Use disposition rows from a Markdown inventory.
    #[arg(long, value_name = "PATH")]
    pub inventory: Option<PathBuf>,

    /// Restore a timestamped migration backup.
    #[arg(long, value_name = "ID", conflicts_with_all = ["dry_run", "write"])]
    pub rollback: Option<String>,

    /// Override the Target home base (for sandboxes and tests).
    #[arg(long, value_name = "SANDBOX")]
    pub root: Option<PathBuf>,
}
