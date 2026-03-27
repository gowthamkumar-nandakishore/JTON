// Error types for parser

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

/// Parse error with approximate position tracking
#[derive(Debug)]
pub struct ParseError {
    pub position: usize,
    pub message: String,
    pub context: Option<String>,
}

impl ParseError {
    pub fn new(position: usize, message: String) -> Self {
        Self {
            position,
            message,
            context: None,
        }
    }

    /// Create error with context extraction
    pub fn with_context(position: usize, message: String, input: &[u8]) -> Self {
        let context = extract_context(input, position);
        Self {
            position,
            message,
            context: Some(context),
        }
    }

    pub fn unexpected_eof(pos: usize) -> Self {
        Self {
            position: pos,
            message: "Unexpected end of input".to_string(),
            context: None,
        }
    }

    pub fn unexpected_token(pos: usize, ch: char) -> Self {
        Self {
            position: pos,
            message: format!("Unexpected token '{}' at position {}", ch, pos),
            context: None,
        }
    }

    pub fn invalid_char(pos: usize, ch: char) -> Self {
        Self {
            position: pos,
            message: format!("Invalid character '{}' at position {}", ch, pos),
            context: None,
        }
    }

    pub fn expected_char(pos: usize, expected: char) -> Self {
        Self {
            position: pos,
            message: format!("Expected '{}' at position {}", expected, pos),
            context: None,
        }
    }

    pub fn expected_token(pos: usize, expected: char) -> Self {
        Self {
            position: pos,
            message: format!("Expected '{}' at position {}", expected, pos),
            context: None,
        }
    }

    pub fn invalid_utf8(pos: usize) -> Self {
        Self {
            position: pos,
            message: format!("Invalid UTF-8 sequence at position {}", pos),
            context: None,
        }
    }

    pub fn invalid_number(pos: usize, num_str: &str) -> Self {
        Self {
            position: pos,
            message: format!("Invalid number '{}' at position {}", num_str, pos),
            context: None,
        }
    }

    pub fn invalid_literal(pos: usize) -> Self {
        Self {
            position: pos,
            message: format!("Invalid literal at position {}", pos),
            context: None,
        }
    }

    pub fn unsupported_feature(pos: usize, feature: &str) -> Self {
        Self {
            position: pos,
            message: format!("Unsupported feature at position {}: {}", pos, feature),
            context: None,
        }
    }

    pub fn unsupported(feature: &str) -> Self {
        Self {
            position: 0,
            message: format!("Not yet implemented: {}", feature),
            context: None,
        }
    }

    pub fn invalid_escape(pos: usize, ch: char) -> Self {
        Self {
            position: pos,
            message: format!("Invalid escape sequence '\\{}' at position {}", ch, pos),
            context: None,
        }
    }

    pub fn invalid_unicode(pos: usize) -> Self {
        Self {
            position: pos,
            message: format!("Invalid Unicode escape at position {}", pos),
            context: None,
        }
    }

    pub fn unescaped_control(pos: usize) -> Self {
        Self {
            position: pos,
            message: format!("Unescaped control character at position {}", pos),
            context: None,
        }
    }

    pub fn invalid_control_char(pos: usize) -> Self {
        Self {
            position: pos,
            message: format!("Unescaped control character at position {}", pos),
            context: None,
        }
    }
}

impl From<ParseError> for PyErr {
    fn from(err: ParseError) -> PyErr {
        let msg = if let Some(context) = err.context {
            format!("{}\n{}", err.message, context)
        } else {
            format!(
                "{} (approximate position: ±32 bytes from {})",
                err.message, err.position
            )
        };
        PyValueError::new_err(msg)
    }
}

impl std::fmt::Display for ParseError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{} at position {}", self.message, self.position)
    }
}

impl std::error::Error for ParseError {}

/// Extract context around an error position (40 chars with caret marker)
fn extract_context(input: &[u8], position: usize) -> String {
    const CONTEXT_SIZE: usize = 40;

    // Calculate excerpt range
    let start = position.saturating_sub(CONTEXT_SIZE / 2);
    let end = (position + CONTEXT_SIZE / 2).min(input.len());

    // Extract excerpt
    let excerpt = &input[start..end];
    let excerpt_str = String::from_utf8_lossy(excerpt);

    // Calculate caret position in excerpt
    let caret_pos = position.saturating_sub(start);

    // Build context string with line numbers and caret
    let mut context = String::new();
    context.push_str(&format!("  at position {}\n", position));
    context.push_str("  | ");
    context.push_str(&excerpt_str.replace('\n', "\\n").replace('\t', "\\t"));
    context.push('\n');
    context.push_str("  | ");
    context.push_str(&" ".repeat(caret_pos));
    context.push('^');

    context
}
