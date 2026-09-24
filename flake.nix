{
  description = "swiftster — SvelteKit + Drizzle + Postgres development environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = {
    self,
    nixpkgs,
  }: let
    systems = ["x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin"];
    forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
  in {
    devShells = forAllSystems (pkgs: {
      default = pkgs.mkShell {
        name = "swiftster";

        packages = with pkgs; [
          # Runtime and package manager — matches "@types/node": "^24" in package.json
          nodejs_24

          # Language servers / formatter for editors
          typescript
          svelte-language-server
          typescript-language-server
          vscode-langservers-extracted
          tailwindcss-language-server
          pyright
          ruff
          prettier

          # psql, pg_dump etc. against the compose.yaml database
          postgresql_17

          # `npm run db:start` needs a compose implementation
          docker-compose

          # Task runner, and the JSON parsing the justfile's tailscale recipes do
          just
          jq

          # python utilities; qrcode renders the printable track codes
          (python3.withPackages (ps: [ps.qrcode]))
        ];

        shellHook = ''
          # Keep `npm i -g` inside the project instead of $HOME, and put
          # locally installed binaries (vite, drizzle-kit, ...) on PATH.
          export NPM_CONFIG_PREFIX="$PWD/.npm-global"
          export PATH="$NPM_CONFIG_PREFIX/bin:$PWD/node_modules/.bin:$PATH"

          echo "swiftster dev shell · node $(node --version) · npm $(npm --version)"
          [ -d node_modules ] || echo "  node_modules missing — run 'npm install'"
          [ -f .env ] || echo "  .env missing — run 'cp .env.example .env'"

          # Interactive `nix develop` lands in bash; hand over to zsh instead.
          # Skipped for `nix develop -c ...`, builds and CI, which are not interactive.
          if [[ $- == *i* ]] && command -v zsh >/dev/null; then
            exec zsh
          fi
        '';
      };
    });

    formatter = forAllSystems (pkgs: pkgs.nixfmt-tree);
  };
}
