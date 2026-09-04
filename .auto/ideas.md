# Autoresearch Ideas - agent-sync optimization

- Improve library scan by reducing file system overhead in sorted_entries
- Cache manifest parsing results to avoid YAML parsing overhead
- Optimize BTreeMap insertion and lookup patterns in scan_root
- Reduce allocations in install mode selection logic
- Improve build time through cargo profile optimization
