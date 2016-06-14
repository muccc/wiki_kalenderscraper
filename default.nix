with import <nixpkgs> {}; {
  pyEnv = stdenv.mkDerivation {
    name = "wiki_kalenderscraper";
    buildInputs = [ stdenv python27Full 
         python27Packages.beautifulsoup4 
         python27Packages.html5lib 
         python27Packages.requests2 
         python27Packages.icalendar 
         python27Packages.pytz
         python27Packages.dateutil
         python27Packages.six];
  };
} 
