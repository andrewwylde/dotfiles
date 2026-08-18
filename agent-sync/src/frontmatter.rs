use anyhow::{bail, Context, Result};
use serde_yaml::{Mapping, Value};

#[derive(Debug, Clone)]
pub struct Markdown {
    pub frontmatter: Value,
    pub body: String,
    pub had_frontmatter: bool,
}

pub fn parse(text: &str) -> Result<Markdown> {
    let Some(rest) = text.strip_prefix("---\n") else {
        return Ok(Markdown {
            frontmatter: Value::Mapping(Mapping::new()),
            body: text.to_owned(),
            had_frontmatter: false,
        });
    };
    let Some(separator) = rest.find("\n---") else {
        bail!("frontmatter starts with '---' but has no closing delimiter");
    };
    let after_separator = &rest[separator + 4..];
    if !after_separator.is_empty() && !after_separator.starts_with('\n') {
        bail!("closing frontmatter delimiter must occupy its own line");
    }
    let yaml = &rest[..separator];
    let frontmatter = if yaml.trim().is_empty() {
        Value::Mapping(Mapping::new())
    } else {
        match serde_yaml::from_str(yaml) {
            Ok(value) => value,
            Err(first) => {
                let repaired = quote_unquoted_description(yaml);
                serde_yaml::from_str(&repaired).context(format!(
                    "parse YAML frontmatter (also failed after quoting description): {first}"
                ))?
            }
        }
    };
    if !frontmatter.is_mapping() {
        bail!("frontmatter must be a YAML mapping");
    }
    Ok(Markdown {
        frontmatter,
        body: after_separator.strip_prefix('\n').unwrap_or("").to_owned(),
        had_frontmatter: true,
    })
}

fn quote_unquoted_description(yaml: &str) -> String {
    let mut out = Vec::new();
    for line in yaml.lines() {
        let Some(rest) = line.strip_prefix("description:") else {
            out.push(line.to_owned());
            continue;
        };
        let value = rest.trim_start();
        if value.is_empty()
            || value.starts_with('"')
            || value.starts_with('\'')
            || value.starts_with('|')
            || value.starts_with('>')
        {
            out.push(line.to_owned());
            continue;
        }
        let escaped = value.replace('\\', "\\\\").replace('"', "\\\"");
        out.push(format!("description: \"{escaped}\""));
    }
    out.join("\n")
}

pub fn render(markdown: &Markdown) -> Result<String> {
    if !markdown.had_frontmatter
        && markdown
            .frontmatter
            .as_mapping()
            .is_some_and(Mapping::is_empty)
    {
        return Ok(markdown.body.clone());
    }

    let mut yaml =
        serde_yaml::to_string(&markdown.frontmatter).context("serialize YAML frontmatter")?;
    if let Some(without_marker) = yaml.strip_prefix("---\n") {
        yaml = without_marker.to_owned();
    }
    while yaml.ends_with('\n') {
        yaml.pop();
    }
    let mut rendered = format!("---\n{yaml}\n---\n");
    if !markdown.body.is_empty() && !markdown.body.starts_with('\n') {
        rendered.push('\n');
    }
    rendered.push_str(&markdown.body);
    Ok(rendered)
}
