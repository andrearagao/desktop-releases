# Desktop releases

Public Linux binary downloads for Folio, Vereda, and Vitals. Application source repositories remain private.

Each application has an independent release tag, such as `folio-v0.1.0`. Archives contain an executable, desktop assets where needed, and dependency license notices. Nix downloads these archives without GitHub credentials and checks their hashes before installation.

The artifacts target NixOS on `aarch64-linux` and `x86_64-linux`. Nix recipes patch the ELF interpreter and library paths and supply runtime dependencies. These archives are not standalone installers for other Linux distributions.

## Build a release

Use the same clean, committed source revision on both native architectures. The build command exports tracked files with `git archive`, excluding local caches and Git metadata. For Folio, the private source repository is `andrearagao/folio`. Vereda and Vitals use their existing private repositories.

```sh
python3 build.py folio /absolute/path/to/folio
```

Replace `folio` with `vereda` or `vitals` for the other applications. The archive command records the source revision and native architecture in `share/release.json`. Publish both architectures and their checksums together. Never replace an existing release asset; publish a new version and update the Nix hashes.

The publisher needs private source access. Installing a published package does not.
