{
  description = "lazyreporting - lazygit-style TUI for Watson + Jira time tracking";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    utils.url = "github:numtide/flake-utils";
    watson-jira-next.url = "github:PrimaMateria/watson-jira-next/feature/config-custom-path";
  };

  outputs = inputs @ {
    self,
    nixpkgs,
    utils,
    ...
  }:
    utils.lib.eachDefaultSystem (
      system: let
        overlay = final: prev: {
          # Wraps watson-jira-next so the config path can be overridden via
          # WATSON_JIRA_CONFIG instead of being hardcoded.
          watson-jira-next-wrapper = prev.writeShellApplication {
            name = "watson-jira";
            text = ''
              CONFIG="''${WATSON_JIRA_CONFIG:-$HOME/.config/watson-jira/config.yaml}"
              ${inputs.watson-jira-next.defaultPackage.x86_64-linux}/bin/watson-jira-next --config "$CONFIG" "$@"
            '';
          };
        };

        pkgs = import nixpkgs {
          inherit system;
          overlays = [overlay];
        };

        # Thin binary so direnv can expose `lr` in PATH. Aliases don't survive
        # direnv — a real script is the documented community solution.
        # Runs from source so code changes don't require direnv reload.
        lrBin = pkgs.writeShellApplication {
          name = "lr";
          text = "python -m lazyreporting \"$@\"";
        };

        # Proper package built from pyproject.toml. The `lr` entry point defined
        # in [project.scripts] is generated automatically by buildPythonApplication.
        # Used for `nix build` and `nix run`; not included in devShell directly.
        lazyreporting = pkgs.python3.pkgs.buildPythonApplication {
          pname = "lazyreporting";
          version = "0.1.0";
          src = ./.;
          pyproject = true;
          build-system = with pkgs.python3.pkgs; [setuptools];
          dependencies = with pkgs.python3.pkgs; [
            textual
            requests
            pyyaml
            python-dateutil
          ];
        };
      in {
        # `nix build` / `nix run` targets the fully built package.
        packages.default = lazyreporting;

        devShell = pkgs.mkShell {
          name = "nix.shell.lazyreporting";

          # inputsFrom pulls in lazyreporting's dependencies without rebuilding
          # the package itself, so source changes are picked up immediately
          # without a direnv reload.
          inputsFrom = [lazyreporting];

          packages = [
            pkgs.watson
            pkgs.watson-jira-next-wrapper
            lrBin
          ];

          shellHook = ''
            export LAZYREPORTING_CONFIG="''${LAZYREPORTING_CONFIG:-$HOME/.config/lazyreporting/config.yaml}"

            if [ ! -f "$LAZYREPORTING_CONFIG" ]; then
              echo "Warning: lazyreporting config not found at $LAZYREPORTING_CONFIG"
              echo "Create it with the following format:"
              echo ""
              echo "  jira:"
              echo "    server: https://your-company.atlassian.net"
              echo "    email: you@example.com"
              echo "    apiToken: <your-api-token>"
              echo "    projects: [PROJ1, PROJ2]"
              echo "    label: Frontend  # optional"
              echo "  watson:"
              echo "    mappings:"
              echo "      - prefix: PROJ1"
              echo "        project: myproject"
              echo "        tags: [sprint]"
              echo "    default:"
              echo "      project: myproject"
              echo "      tags: [other]"
            fi

            echo "nix.shell.lazyreporting"
            echo "  lr     - launch TUI"
            echo "  Config: $LAZYREPORTING_CONFIG"
          '';
        };
      }
    );
}
