# Autoresearch Ideas - agent-sync optimization

## Key Constraint Discovered
- Windows MSVC toolchain broken (missing dlltool.exe) → **WSL cargo build works!**
- Binary must be built on WSL/Linux to validate optimizations
- Current binary at /c/Users/drewk/dotfiles/agent-sync/target/release/agent-sync

## Dead Ends Explored
- Manifest cache: NET NEGATIVE - 99.4% miss rate (only 2/358 items have manifest.toml), HashMap lookup overhead > toml parsing savings
- Sort by_key syntax changes: no effect (compiler produces identical code)
- Adding is_file + extension match for tombstone: no measurable benefit (rare code path)
- Direct file_name() method: no effect (identical to fs::DirEntry::file_name)

## Promising Directions (Not Yet Tried)

### High-Impact Opportunities
1. **Avoid `to_string_lossy().into_owned()`** in hot loops - use OsString directly for comparisons
2. **Pre-allocate BTreeMap capacity** with `BTreeMap::with_capacity(n)` based on directory size hints
3. **Skip redundant directory checks** - current code checks is_dir() multiple times per item
4. **Parallel library scanning** - scan each Kind in parallel with rayon

### Allocation Reduction
- **Vendor origin string cloning** - origin.clone() called twice per item in insert_candidate
- **PathBuf allocations** - path.join() called 2-3 times per item (tombstone + source_file + manifest.toml)
- **Use `OsStr` for comparisons** - avoid String conversion for filesystem checks

## Environment Notes
- WSL cargo build works: `~/.cargo/bin/cargo build --release --manifest-path /mnt/c/Users/drewk/dotfiles/agent-sync/Cargo.toml`
- Benchmark variance: ~15% (improved from initial 300%)
- Binary timestamp shown in WSL via `ls -la`
