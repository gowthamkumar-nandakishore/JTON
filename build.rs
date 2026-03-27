fn main() {
    println!("cargo:rerun-if-changed=build.rs");

    let target_arch = std::env::var("CARGO_CFG_TARGET_ARCH").unwrap();
    match target_arch.as_str() {
        "x86_64" => println!(
            "cargo:warning=Building JTON for x86_64 - AVX2 support will be checked at runtime"
        ),
        "aarch64" => println!("cargo:warning=Building JTON for aarch64 - NEON SIMD will be used"),
        arch => println!("cargo:warning=Building JTON for {arch} - scalar fallback will be used"),
    }
}

