fn main() {
    // Check for AVX2 support at compile time
    // This enforces the Constitution requirement that AVX2 is mandatory
    
    println!("cargo:rerun-if-changed=build.rs");
    
    // Warn if compiling for non-x86_64 targets
    let target_arch = std::env::var("CARGO_CFG_TARGET_ARCH").unwrap();
    if target_arch != "x86_64" {
        panic!("ZSON requires x86_64 architecture with AVX2 support (2013+ CPUs)");
    }
    
    // Note: Runtime feature detection is done in lib.rs
    // This is just a build-time sanity check
    println!("cargo:warning=Building ZSON for x86_64 - AVX2 support will be checked at runtime");
}
