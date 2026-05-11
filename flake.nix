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
            export WATSON_JIRA_CONFIG="''${WATSON_JIRA_CONFIG:-$HOME/.config/watson-jira/config.yaml}"

            alias lr="python -m lazyreporting"

            if [ ! -f "$WATSON_JIRA_CONFIG" ]; then
              echo "Warning: watson-jira config not found at $WATSON_JIRA_CONFIG"
              echo "Create it with the following format:"
              echo ""
              echo "  jira:"
              echo "    server: https://finapi.jira.com/"
              echo "    cookie: <your-session-cookie>"
              echo "  mappings:"
              echo "    - name: sprint"
              echo "      type: issue_specified_in_tag"
              echo "    - name: other"
              echo "      type: single_issue"
              echo "      issue: DATAINT-3511"
            fi

            echo "nix.shell.lazyreporting"
            echo "  lr     - launch TUI"
            echo "  Config: $WATSON_JIRA_CONFIG"
          '';
        };
      }
    );
}
