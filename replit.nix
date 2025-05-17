{ pkgs }: {
  deps = [
    pkgs.python310Full
    pkgs.python310Packages.aiogram
    pkgs.python310Packages.requests
    pkgs.python310Packages.python_dotenv
    pkgs.python310Packages.matplotlib
    pkgs.google-cloud-sdk
  ];
}
