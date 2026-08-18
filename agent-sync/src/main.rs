mod cli;
mod config;
mod doctor;
mod frontmatter;
mod hooks;
mod install;
mod library;
mod list;
mod manifest;
mod migrate;
mod overlay;
mod state;
mod sync;
mod target;
mod verify;

use anyhow::{bail, Result};
use clap::Parser;

use crate::cli::{Cli, Command};
use crate::config::Config;

fn main() -> Result<()> {
    let cli = Cli::parse();
    match cli.command {
        Command::Sync(args) => {
            let config = Config::discover(args.root)?;
            sync::run(&config, args.dry_run)
        }
        Command::Verify(args) => {
            let config = Config::discover(args.root)?;
            if verify::run(&config)? {
                Ok(())
            } else {
                bail!("verification failed")
            }
        }
        Command::List(args) => {
            let config = Config::discover(args.root)?;
            list::run(&config)
        }
        Command::Migrate(args) => {
            let config = Config::discover(args.root.clone())?;
            migrate::run(&config, &args)
        }
        Command::Doctor(args) => {
            let config = Config::discover(args.root)?;
            doctor::run(&config, args.fix)
        }
    }
}
