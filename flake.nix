{
  description = "Build Linux desktop release artifacts from private application sources";
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/b25309931cfda5f0b8805f462a29897eeae50168";
    nixpkgs-unstable.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    rust-overlay = {
      url = "github:oxalica/rust-overlay";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    app-source = {
      url = "path:./empty-source";
      flake = false;
    };
  };
  outputs =
    {
      nixpkgs,
      nixpkgs-unstable,
      rust-overlay,
      app-source,
      ...
    }:
    let
      systems = [
        "aarch64-linux"
        "x86_64-linux"
      ];
    in
    {
      packages = nixpkgs.lib.genAttrs systems (
        system:
        let
          pkgs = import nixpkgs {
            inherit system;
            config = { };
            overlays = [ rust-overlay.overlays.default ];
          };
          unstable = import nixpkgs-unstable {
            inherit system;
            config = { };
            overlays = [ ];
          };
        in
        builtins.listToAttrs (
          map
            (app: {
              name = app;
              value = pkgs.callPackage ./build.nix {
                inherit app;
                source = app-source;
                zig = unstable.zig_0_17;
              };
            })
            (
              nixpkgs.lib.optionals (builtins.pathExists (app-source + "/Cargo.toml")) [
                "folio"
                "vereda"
                "vitals"
              ]
            )
        )
        // {
          release-tools = pkgs.writeShellApplication {
            name = "desktop-release-archive";
            runtimeInputs = [
              pkgs.python3
              pkgs.patchelf
              pkgs.nix
            ];
            text = ''exec python3 ${./.}/archive.py "$@"'';
          };
        }
      );
    };
}
