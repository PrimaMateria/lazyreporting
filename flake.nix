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
          # watson-jira wrapper that reads config path from WATSON_JIRA_CONFIG env var
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

        pythonEnv = pkgs.python3.withPackages (ps:
          with ps; [
            textual
            requests
            pyyaml
            python-dateutil
          ]);
      in {
        devShell = pkgs.mkShell {
          name = "nix.shell.lazyreporting";
          packages = [
            pkgs.watson
            pkgs.watson-jira-next-wrapper
            pythonEnv
          ];
          shellHook = ''
            export LAZYREPORTING_CONFIG="''${LAZYREPORTING_CONFIG:-$HOME/.config/lazyreporting/config.yaml}"

            alias lr="python -m lazyreporting"

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
