{
  description = "MuCCC Wiki Kalenderscraper";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  inputs.flake-utils.url = "github:numtide/flake-utils";

  outputs = { self, nixpkgs, flake-utils, ... }: rec {
    overlay = final: prev: {
      muccc-wiki-kalenderscraper = import ./default.nix { pkgs = final; };
    };
  } // (flake-utils.lib.eachDefaultSystem (system:
    let
      pkgs = import nixpkgs {
        inherit system;
        overlays = [ self.overlay ];
      };
      in
      rec {
        defaultPackage = self.packages.${system}.muccc-wiki-kalenderscraper;
        packages.muccc-wiki-kalenderscraper = pkgs.muccc-wiki-kalenderscraper;
        devShell = pkgs.mkShell {
          inputsFrom = [ defaultPackage ];
          packages = [ defaultPackage.dependencyEnv pkgs.poetry ];
      };
    }
  ));
}
