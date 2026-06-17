fn main() {
    prost_build::Config::new()
        .compile_protos(
            &[
                "../proto/wcms/v1/common.proto",
                "../proto/wcms/v1/realtime.proto",
            ],
            &["../proto"],
        )
        .expect("prost-build failed to compile proto files");
}
