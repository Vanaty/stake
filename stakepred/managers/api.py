"""
API client for Stake Crash Predictor.
Handles GraphQL communication with Stake API.
"""

import json
from typing import Optional, TYPE_CHECKING

from ..logger import get_logger

if TYPE_CHECKING:
    from patchright.async_api import Page

logger = get_logger("StakeAPIClient")


class StakeAPIClient:
    """Client pour interagir avec l'API GraphQL de Stake."""

    def __init__(self, page: "Page"):
        self.page = page

    async def place_crash_bet(self, amount: float, cashout_multiplier: float) -> tuple[bool, str]:
        """Place réellement un pari sur l'interface Stake Crash via le navigateur.

        Retourne (success, message).
        """
        if amount <= 0:
            return False, "Montant de pari invalide"

        if cashout_multiplier <= 1:
            return False, "Multiplicateur auto-cashout invalide"

        result = await self.page.evaluate(
            """
            async ({ amount, cashoutMultiplier }) => {
                const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

                const isVisible = (el) => {
                    if (!el) return false;
                    const style = window.getComputedStyle(el);
                    const rect = el.getBoundingClientRect();
                    return (
                        style.visibility !== 'hidden' &&
                        style.display !== 'none' &&
                        rect.width > 0 &&
                        rect.height > 0
                    );
                };

                const setInputValue = (input, value) => {
                    const proto = Object.getPrototypeOf(input);
                    const descriptor = Object.getOwnPropertyDescriptor(proto, 'value');
                    if (descriptor && descriptor.set) {
                        descriptor.set.call(input, String(value));
                    } else {
                        input.value = String(value);
                    }
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                };

                const candidates = Array.from(
                    document.querySelectorAll('input[type="text"], input[type="number"], input:not([type])')
                ).filter(isVisible);

                const amountInput =
                    candidates.find((el) => {
                        const p = (el.placeholder || '').toLowerCase();
                        const a = (el.getAttribute('aria-label') || '').toLowerCase();
                        return p.includes('amount') || p.includes('montant') || p.includes('bet') || a.includes('amount') || a.includes('bet');
                    }) || candidates[0];

                const autoCashoutInput =
                    candidates.find((el) => {
                        const p = (el.placeholder || '').toLowerCase();
                        const a = (el.getAttribute('aria-label') || '').toLowerCase();
                        return p.includes('cashout') || p.includes('auto') || a.includes('cashout') || a.includes('auto');
                    }) || candidates[1];

                if (!amountInput) {
                    return { success: false, message: 'Champ montant introuvable' };
                }

                amountInput.focus();
                setInputValue(amountInput, amount.toFixed(8).replace(/0+$/, '').replace(/\.$/, ''));

                if (autoCashoutInput) {
                    autoCashoutInput.focus();
                    setInputValue(autoCashoutInput, cashoutMultiplier.toFixed(2));
                }

                await sleep(120);

                const betButtons = Array.from(document.querySelectorAll('button')).filter((btn) => {
                    if (!isVisible(btn) || btn.disabled) return false;
                    const txt = (btn.innerText || btn.textContent || '').toLowerCase();
                    return (
                        txt.includes('bet') ||
                        txt.includes('parier') ||
                        txt.includes('place bet') ||
                        txt.includes('placer')
                    );
                });

                if (!betButtons.length) {
                    return { success: false, message: 'Bouton Bet introuvable' };
                }

                const button = betButtons[0];
                button.click();

                await sleep(220);

                const cashoutBtnVisible = Array.from(document.querySelectorAll('button')).some((btn) => {
                    if (!isVisible(btn)) return false;
                    const txt = (btn.innerText || btn.textContent || '').toLowerCase();
                    return txt.includes('cashout') || txt.includes('encaisser');
                });

                if (cashoutBtnVisible) {
                    return { success: true, message: 'Pari placé (bouton Cashout visible)' };
                }

                // Si l'UI ne confirme pas clairement, on renvoie un succès prudent
                // si le clic a été effectué (à vérifier côté websocket/résultat round).
                return { success: true, message: 'Clic Bet envoyé (confirmation UI partielle)' };
            }
            """,
            {"amount": amount, "cashoutMultiplier": cashout_multiplier},
        )

        success = bool(result and result.get("success"))
        message = str(result.get("message", "Réponse inconnue")) if isinstance(result, dict) else "Réponse invalide"
        if success:
            logger.success(f"Pari réel envoyé sur la plateforme: {message}")
        else:
            logger.warning(f"Échec placement pari réel: {message}")

        return success, message

    async def fetch_graphql(
        self, 
        query: str, 
        variables: dict, 
        operation_name: Optional[str] = None
    ) -> dict:
        """Exécute une requête GraphQL."""
        response = await self.page.evaluate(f"""
            async () => {{
                const res = await fetch('https://stake.com/_api/graphql', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        query: `{query}`,
                        variables: {json.dumps(variables)},
                        operationName: {json.dumps(operation_name)}
                    }})
                }});
                return await res.json();
            }}
        """)
        return response

    async def fetch_user_balance(self) -> Optional[float]:
        """Récupère le solde USDC de l'utilisateur."""
        response = await self.fetch_graphql(
            query="""
                query UserVaultBalances {
                    user {
                        id
                        balances {
                            available {
                                amount
                                currency
                            }
                            vault {
                                amount
                                currency
                            }
                        }
                    }
                }
            """,
            variables={},
            operation_name="UserVaultBalances"
        )
        
        if response.get('errors'):
            logger.error(f"Erreur lors de la récupération des données utilisateur: {response['errors']}")
            return None
        
        user_data = response.get('data', {}).get('user', {})
        balances = user_data.get('balances', [])
        
        for balance in balances:
            if balance.get('available', {}).get('currency', '').upper() == 'USDC':
                return balance.get('available', {}).get('amount')
        
        return None

    async def fetch_game_hash(self, game_id: str) -> Optional[str]:
        """Récupère le hash du jeu pour un game_id donné."""
        if not game_id:
            logger.error("Game ID non fourni")
            return None
        
        max_retries = 3
        for attempt in range(max_retries):
            hash_val = await self.fetch_graphql(
                query="""
                    query CrashGameLookup($gameId: String!) {
                        crashGame(gameId: $gameId) {
                            hash {
                                hash
                            }
                        }
                    }
                """,
                variables={"gameId": game_id},
                operation_name="CrashGameLookup"
            )
            
            game_hash = hash_val.get('data', {}).get('crashGame', {}).get('hash', {}).get('hash')
            if game_hash:
                logger.debug(f"Hash du jeu trouvé: {game_hash}")
                return game_hash
            
            if attempt < max_retries - 1:
                logger.warning(f"Hash du jeu non trouvé, tentative {attempt + 1}/{max_retries}")
                import asyncio
                await asyncio.sleep(1)
        
        logger.error(f"Impossible de récupérer le hash pour le game_id {game_id}")
        return None

    async def fetch_crash_history(self, limit: int = 10, offset: int = 0) -> list[dict]:
        """Récupère l'historique des crashes."""
        histories = []
        x = limit // 10
        
        for _ in range(x):
            off_set = len(histories) + offset
            lim = 10

            history = await self.fetch_graphql(
                query="""
                    query CrashGameListHistory($limit: Int, $offset: Int) {
                        crashGameList(limit: $limit, offset: $offset) {
                        id
                        startTime
                        crashpoint
                        hash {
                            id
                            hash
                        }
                        }
                    }
                """,
                variables={"limit": min(lim, 50), "offset": off_set},
                operation_name="CrashGameListHistory"
            )
            
            if history.get('errors'):
                logger.error(f"Erreur lors de la récupération de l'historique: {history['errors']}")
                break
            
            histories.extend(history.get('data', {}).get('crashGameList', []))
        
        return histories
