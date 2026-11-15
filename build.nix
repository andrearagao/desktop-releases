{
  lib,
  callPackage,
  rust-bin,
  makeRustPlatform,
  fetchgit,
  applyPatches,
  pkg-config,
  zig,
  app,
  source,
}:
let
  toolchain = rust-bin.stable."1.99.0".default;
  rustPlatform = makeRustPlatform {
    cargo = toolchain;
    rustc = toolchain;
  };
  rune =
    if app == "folio" then
      applyPatches {
        name = "folio-rune-source";
        src = fetchgit {
          url = "https://github.com/anomalyco/rune";
          rev = "7ead7d63fcf6f9dd9669385a8b90e2ae80015d7b";
          hash = "sha256-e6f1kr0qvTT13YKZIGhiFee33RwydeVX60Yz23j/cQA=";
          fetchSubmodules = true;
        };
        patches = map (path: source + path) (
          [
            "/experiments/opengl/rune-gpu-setup.patch"
            "/experiments/opengl/rune-opengl.patch"
            "/nix/rune-font-loading.patch"
            "/nix/rune-hardware-policy.patch"
          ]
          ++ lib.optional (builtins.pathExists (
            source + "/nix/rune-keyboard-focus.patch"
          )) "/nix/rune-keyboard-focus.patch"
        );
      }
    else
      callPackage (source + "/nix/rune-source.nix") { };
  libraries =
    with (callPackage (
      {
        glib,
        cairo,
        pango,
        gdk-pixbuf,
        wayland,
        libxkbcommon,
        libx11,
        libxcursor,
        libxi,
        libxrandr,
      }:
      {
        inherit
          glib
          cairo
          pango
          gdk-pixbuf
          wayland
          libxkbcommon
          libx11
          libxcursor
          libxi
          libxrandr
          ;
      }
    ) { });
    [
      wayland
      libxkbcommon
      libx11
      libxcursor
      libxi
      libxrandr
    ]
    ++ lib.optionals (app == "vereda") [
      glib
      cairo
      pango
      gdk-pixbuf
    ];
in
rustPlatform.buildRustPackage {
  pname = app;
  version = (builtins.fromTOML (builtins.readFile (source + "/Cargo.toml"))).package.version;
  src = source;
  cargoLock.lockFile = source + "/Cargo.lock";
  postPatch = "ln -s ${rune} .rune-source";
  nativeBuildInputs = [
    pkg-config
    zig
  ]
  ++ lib.optional (app == "vereda") rustPlatform.bindgenHook;
  buildInputs = libraries;
  dontUseZigConfigure = true;
  dontUseZigBuild = true;
  dontUseZigCheck = true;
  dontUseZigInstall = true;
  doCheck = false;
  env.CARGO_PROFILE_RELEASE_CODEGEN_UNITS = "16";
  postInstall =
    lib.optionalString (app == "vereda") ''
      cp -r share "$out/share"
      install -Dm644 LICENSE THIRD_PARTY_NOTICES.md -t "$out/share/licenses/vereda"
    ''
    + ''
      mkdir -p "$out/share/licenses/rune"
      find ${rune} -maxdepth 1 -type f \( -iname 'license*' -o -iname '*notice*' \) -exec cp {} "$out/share/licenses/rune/" \;
    '';
  meta = {
    platforms = [
      "aarch64-linux"
      "x86_64-linux"
    ];
    mainProgram = if app == "folio" then "folio-rune" else app;
  };
}
