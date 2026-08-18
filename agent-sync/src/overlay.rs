use anyhow::{bail, Result};
use serde_yaml::Value;

use crate::frontmatter::{self, Markdown};
use crate::manifest::Overlay;

pub fn apply(source: &str, overlay: &Overlay) -> Result<String> {
    let mut markdown = frontmatter::parse(source)?;
    if let Some(map) = overlay.frontmatter.as_mapping() {
        if !map.is_empty() {
            deep_merge(&mut markdown.frontmatter, overlay.frontmatter.clone())?;
            markdown.had_frontmatter = true;
        }
    } else if !overlay.frontmatter.is_null() {
        bail!("frontmatter overlay must be a mapping");
    }
    markdown.body.push_str(&overlay.body_append);
    frontmatter::render(&Markdown {
        frontmatter: markdown.frontmatter,
        body: markdown.body,
        had_frontmatter: markdown.had_frontmatter,
    })
}

fn deep_merge(base: &mut Value, overlay: Value) -> Result<()> {
    if matches!(*base, Value::Null) {
        *base = Value::Mapping(serde_yaml::Mapping::new());
    }
    match (base, overlay) {
        (Value::Mapping(base_map), Value::Mapping(overlay_map)) => {
            for (key, value) in overlay_map {
                if let Some(base_value) = base_map.get_mut(&key) {
                    if base_value.is_mapping() && value.is_mapping() {
                        deep_merge(base_value, value)?;
                    } else {
                        *base_value = value;
                    }
                } else {
                    base_map.insert(key, value);
                }
            }
            Ok(())
        }
        (_, Value::Mapping(_)) => bail!("frontmatter base must be a mapping"),
        _ => bail!("frontmatter overlay must be a mapping"),
    }
}

#[cfg(test)]
mod tests {
    use serde_yaml::Value;

    use super::apply;
    use crate::manifest::Overlay;

    #[test]
    fn deep_merges_nested_frontmatter_and_appends_body() {
        let overlay = Overlay {
            frontmatter: serde_yaml::from_str::<Value>(
                "metadata:\n  source: cursor\ndisable-model-invocation: true\n",
            )
            .expect("valid YAML"),
            body_append: "\ncursor only\n".to_owned(),
        };
        let source = "---\nname: demo\nmetadata:\n  source: public\n  keep: yes\n---\n\nbody\n";

        let rendered = apply(source, &overlay).expect("overlay applied");

        assert!(rendered.contains("source: cursor"));
        assert!(rendered.contains("keep: yes"));
        assert!(rendered.contains("disable-model-invocation: true"));
        assert!(rendered.ends_with("body\n\ncursor only\n"));
    }

    #[test]
    fn null_overlay_leaves_body() {
        let overlay = Overlay::default();
        let source = "---\nname: demo\n---\n\nbody\n";
        let rendered = apply(source, &overlay).expect("apply");
        assert!(rendered.contains("name: demo"));
        assert!(rendered.contains("body"));
    }
}
