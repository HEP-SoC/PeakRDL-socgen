{
  description = "PeakRDL-socgen";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/02263f46911178e286242786fd6ea1d229583fbb";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        python = pkgs.python3;

        peakrdl-socgen = python.pkgs.buildPythonPackage {
          pname = "peakrdl-socgen";
          version = "0.1.5";
          format = "setuptools";

          src = self;

          propagatedBuildInputs = with python.pkgs; [
            jinja2
            peakrdl
            systemrdl-compiler
          ];
        };
      in
      {
        packages.default = peakrdl-socgen;

        devShells.default = pkgs.mkShell {
          packages = [ (python.withPackages ( ps: [ peakrdl-socgen]))
                     ];
        };
      }
    );
}
