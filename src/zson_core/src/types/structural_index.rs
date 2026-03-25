/// Structural index from SIMD scanner
/// Contains positions of all delimiter characters
#[derive(Debug, Default)]
pub struct StructuralIndex {
    /// Positions of `{`
    pub open_braces: Vec<usize>,
    
    /// Positions of `[`
    pub open_brackets: Vec<usize>,
    
    /// Positions of `:`
    pub colons: Vec<usize>,
    
    /// Positions of `;` (Zen Grid row separators)
    pub semicolons: Vec<usize>,
    
    /// Positions of `,`
    pub commas: Vec<usize>,
    
    /// Positions of `]`
    pub close_brackets: Vec<usize>,
    
    /// Positions of `}`
    pub close_braces: Vec<usize>,
    
    /// Positions of `"` (string delimiters) — enables zero-copy string extraction
    /// Allows direct jumping between quotes for zero-copy string extraction
    pub quotes: Vec<usize>,
}

impl StructuralIndex {
    /// Create with pre-allocated capacity based on input size.
    /// Avoids repeated Vec reallocations during SIMD scanning.
    /// Capacities are tuned for typical JSON density (~1 structural char per 4 bytes).
    pub fn with_input_capacity(input_len: usize) -> Self {
        Self {
            quotes:          Vec::with_capacity(input_len / 8),   // ~1 quote per 8 bytes
            colons:          Vec::with_capacity(input_len / 26),  // ~1 colon per key-value pair
            commas:          Vec::with_capacity(input_len / 20),  // ~1 comma per value
            open_braces:     Vec::with_capacity(input_len / 80),
            close_braces:    Vec::with_capacity(input_len / 80),
            open_brackets:   Vec::with_capacity(input_len / 80),
            close_brackets:  Vec::with_capacity(input_len / 80),
            semicolons:      Vec::new(), // rare — only in Zen Grid
        }
    }
}
