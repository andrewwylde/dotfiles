use anyhow::Result;

use crate::config::Config;
use crate::hooks;
use crate::install;
use crate::library::{Kind, Library};
use crate::state::State;
use crate::sync;
use crate::target::Target;

/// Returns `Ok(true)` when verification passes.
pub fn run(config: &Config) -> Result<bool> {
    let library = Library::scan(config)?;
    for diagnostic in &library.diagnostics {
        eprintln!("WARN {}", diagnostic.message);
    }

    let mut ok = true;
    let expected = sync::expected_markdown(config, &library)?;
    let state = State::load(&config.state_file)?;

    for item in &expected {
        if item.excluded {
            continue;
        }
        if !install::path_exists(&item.destination) {
            eprintln!(
                "ERROR missing {}/{} at {}",
                item.kind,
                item.item_name,
                item.destination.display()
            );
            ok = false;
            continue;
        }
        if item.target == Target::Cursor
            && std::fs::symlink_metadata(&item.destination)
                .ok()
                .is_some_and(|meta| meta.file_type().is_symlink())
        {
            eprintln!(
                "ERROR cursor install must be a copy, found symlink {}",
                item.destination.display()
            );
            ok = false;
        }
        let actual = std::fs::read_to_string(&item.main_destination).unwrap_or_default();
        if actual != item.content {
            eprintln!(
                "ERROR content drift {}/{} -> {}",
                item.kind,
                item.item_name,
                item.main_destination.display()
            );
            ok = false;
        }
        if !state.owns(&item.destination) {
            eprintln!(
                "WARN {} not recorded in state {}",
                item.destination.display(),
                config.state_file.display()
            );
        }
    }

    let packs = library
        .items
        .iter()
        .filter(|item| item.kind == Kind::Hooks)
        .collect::<Vec<_>>();
    if !hooks::verify(config, &packs)? {
        ok = false;
    }

    if ok {
        println!("OK verify passed");
    }
    Ok(ok)
}
