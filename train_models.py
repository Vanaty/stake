"""Script CLI pour entraîner les modèles de prédiction à partir du CSV historique."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from stakepred.logger import get_logger
from stakepred.managers.predictor import (
	DEFAULT_TARGET_MULTIPLIER,
	FEATURE_ROUNDS,
	MIN_DATA_TO_TRAIN,
	MODEL_CLASS_FILE,
	MODEL_REG_FILE,
	AdvancedPredictor,
)


logger = get_logger("TrainModels")


def build_parser() -> argparse.ArgumentParser:
	"""Construit le parser CLI."""
	parser = argparse.ArgumentParser(
		description="Entraîne les modèles de classification et de régression sur crash_history.csv"
	)
	parser.add_argument(
		"--csv",
		type=Path,
		default=Path("crash_history.csv"),
		help="Chemin vers le dataset CSV (défaut: crash_history.csv)",
	)
	parser.add_argument(
		"--target",
		type=float,
		default=DEFAULT_TARGET_MULTIPLIER,
		help=f"Multiplicateur cible (défaut: {DEFAULT_TARGET_MULTIPLIER})",
	)
	parser.add_argument(
		"--n-lags",
		type=int,
		default=FEATURE_ROUNDS,
		help=f"Nombre de rounds utilisés comme features (défaut: {FEATURE_ROUNDS})",
	)
	parser.add_argument(
		"--min-rows",
		type=int,
		default=MIN_DATA_TO_TRAIN,
		help=f"Nombre minimum d'échantillons pour entraîner (défaut: {MIN_DATA_TO_TRAIN})",
	)
	parser.add_argument(
		"--alpha",
		type=float,
		default=0.3,
		help="Alpha pour l'EMA dans les features (défaut: 0.3)",
	)
	parser.add_argument(
		"--weight-type",
		choices=["linear", "exponential", "uniform"],
		default="linear",
		help="Type de pondération des features temporelles",
	)
	parser.add_argument(
		"--clf-model",
		type=Path,
		default=Path(MODEL_CLASS_FILE),
		help=f"Chemin de sauvegarde du modèle classifieur (défaut: {MODEL_CLASS_FILE})",
	)
	parser.add_argument(
		"--reg-model",
		type=Path,
		default=Path(MODEL_REG_FILE),
		help=f"Chemin de sauvegarde du modèle régression (défaut: {MODEL_REG_FILE})",
	)
	parser.add_argument(
		"--metadata",
		type=Path,
		default=Path("training_metadata.json"),
		help="Fichier JSON de metadata d'entraînement",
	)
	return parser


def _normalize_weight_type(weight_type: str) -> str:
	"""Convertit l'option CLI en valeur attendue par le prédicteur."""
	return "ones" if weight_type == "uniform" else weight_type


def _validate_args(args: argparse.Namespace) -> None:
	"""Valide les arguments CLI et lève ValueError si invalides."""
	if not args.csv.exists():
		raise ValueError(f"Dataset introuvable: {args.csv}")
	if args.n_lags <= 1:
		raise ValueError("--n-lags doit être > 1")
	if args.min_rows <= 0:
		raise ValueError("--min-rows doit être > 0")
	if args.target <= 1.0:
		raise ValueError("--target doit être > 1.0")
	if not (0.0 < args.alpha < 1.0):
		raise ValueError("--alpha doit être strictement entre 0 et 1")


def train_and_save(args: argparse.Namespace) -> dict[str, float | int | str]:
	"""Exécute l'entraînement, sauvegarde les modèles et retourne les métriques."""
	predictor = AdvancedPredictor(
		target=args.target,
		n_lags=args.n_lags,
		alpha=args.alpha,
		weight_type=_normalize_weight_type(args.weight_type),
	)

	metrics = predictor.train_models_from_csv(
		csv_path=str(args.csv),
		min_rows=args.min_rows,
	)

	args.clf_model.parent.mkdir(parents=True, exist_ok=True)
	args.reg_model.parent.mkdir(parents=True, exist_ok=True)
	args.metadata.parent.mkdir(parents=True, exist_ok=True)

	predictor.save_models(clf_path=str(args.clf_model), reg_path=str(args.reg_model))

	metadata = {
		"trained_at": datetime.now(timezone.utc).isoformat(),
		"csv_path": str(args.csv.resolve()),
		"model_classification": str(args.clf_model.resolve()),
		"model_regression": str(args.reg_model.resolve()),
		"target": args.target,
		"n_lags": args.n_lags,
		"alpha": args.alpha,
		"weight_type": args.weight_type,
		"min_rows": args.min_rows,
		"metrics": metrics,
	}
	args.metadata.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

	return {
		"accuracy": float(metrics["accuracy"]),
		"log_loss": float(metrics["log_loss"]),
		"mse": float(metrics["mse"]),
		"n_samples": int(metrics["n_samples"]),
		"clf_model": str(args.clf_model),
		"reg_model": str(args.reg_model),
		"metadata": str(args.metadata),
	}


def main() -> int:
	"""Point d'entrée du script."""
	parser = build_parser()
	args = parser.parse_args()

	try:
		_validate_args(args)
		result = train_and_save(args)
	except Exception as exc:
		logger.error(f"Échec entraînement: {exc}")
		return 1

	logger.success(
		"Entraînement terminé | "
		f"samples={result['n_samples']} | "
		f"accuracy={result['accuracy']:.4f} | "
		f"log_loss={result['log_loss']:.4f} | "
		f"mse={result['mse']:.4f}"
	)
	logger.info(f"Modèle classification: {result['clf_model']}")
	logger.info(f"Modèle régression: {result['reg_model']}")
	logger.info(f"Metadata: {result['metadata']}")
	return 0


if __name__ == "__main__":
	sys.exit(main())
