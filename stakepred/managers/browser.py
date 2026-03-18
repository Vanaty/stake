"""
Browser manager for Stake Crash Predictor.
Handles Playwright browser lifecycle.
"""

import os
import shutil
import subprocess
from typing import Optional

from ..logger import get_logger

logger = get_logger("BrowserManager")

USER_DATA_DIR = r"./session_data"

try:
    from pyvirtualdisplay import Display
except ImportError:
    Display = None


class BrowserManager:
    """Gère le cycle de vie du navigateur Playwright."""

    def __init__(
        self,
        enable_pyvirtual: bool = False,
        enable_vnc: bool = False,
        vnc_port: int = 5900,
        vnc_password: Optional[str] = None,
    ):
        self.context = None
        self.crash_page = None
        self.playwright = None
        self.virtual_display = None
        self.vnc_process: Optional[subprocess.Popen] = None
        self.enable_pyvirtual = enable_pyvirtual
        self.enable_vnc = enable_vnc
        self.vnc_port = vnc_port
        self.vnc_password = vnc_password

    async def initialize(self):
        """Initialise le navigateur et la page."""
        from patchright.async_api import async_playwright

        if self.enable_vnc and not self.enable_pyvirtual:
            logger.info("VNC demandé: activation automatique de pyvirtualdisplay")
            self.enable_pyvirtual = True
        
        if self.enable_pyvirtual:
            self._setup_virtual_display()
            if self.enable_vnc:
                self._start_vnc_server()
        
        self.playwright = await async_playwright().start()
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            locale='fr-FR',
        )
        self.crash_page = await self.context.new_page()
        logger.info("Navigateur initialisé avec succès")

    def _setup_virtual_display(self):
        """Configure l'affichage virtuel pour le débogage."""
        if Display is None:
            logger.warning("pyvirtualdisplay n'est pas installé.")
            return
        
        visible = int(os.getenv("PYVIRTUAL_VISIBLE", "0"))
        self.virtual_display = Display(
            visible=visible,
            size=(1920, 1080),
            backend=os.getenv("PYVIRTUAL_BACKEND", "xvfb"),
        )
        self.virtual_display.start()
        logger.info(f"Affichage virtuel activé sur {os.environ.get('DISPLAY', 'DISPLAY inconnu')}")

    def _start_vnc_server(self):
        """Démarre un serveur VNC (x11vnc) sur l'affichage virtuel."""
        if os.name != "posix":
            logger.warning("VNC n'est supporté que sur Linux/Unix")
            return

        if self.virtual_display is None:
            logger.warning("Impossible de démarrer VNC sans affichage virtuel")
            return

        if shutil.which("x11vnc") is None:
            logger.warning("x11vnc non trouvé. Installez-le: sudo apt install x11vnc")
            return

        display = os.environ.get("DISPLAY")
        if not display:
            display = f":{self.virtual_display.display}"

        command = [
            "x11vnc",
            "-display", display,
            "-forever",
            "-shared",
            "-rfbport", str(self.vnc_port),
            "-localhost",
        ]

        if self.vnc_password:
            command.extend(["-passwd", self.vnc_password])
        else:
            command.append("-nopw")

        self.vnc_process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info(f"VNC démarré sur 127.0.0.1:{self.vnc_port} (display {display})")

    async def close(self):
        """Ferme le navigateur et libère les ressources."""
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
        if self.vnc_process and self.vnc_process.poll() is None:
            self.vnc_process.terminate()
            logger.info("Serveur VNC arrêté")
        if self.virtual_display:
            self.virtual_display.stop()
            logger.info("Affichage virtuel fermé")

    async def navigate_to_game(self):
        """Navigue vers la page du jeu Crash."""
        await self.crash_page.goto("https://stake.com/fr/casino/games/crash", timeout=1200000)
        loader_selector = "img.loader[src*='Stake-preloader']"

        try:
            await self.crash_page.wait_for_selector(
                loader_selector,
                state="hidden",
                timeout=120000,
            )
            logger.info("Loader disparu, page Crash prête")
        except Exception:
            logger.warning("Timeout attente loader: on continue malgré tout")

        logger.info("Navigation vers le jeu effectuée")
