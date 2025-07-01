import sqlite3
from pathlib import Path

import pickle

from src.analysis import ml_trainer


def _create_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE trade_log (entry_price REAL, exit_price REAL, entry_time INT, exit_time INT, volume REAL)"
    )
    # create synthetic trades alternating win/loss
    for i in range(10):
        entry = 100 + i
        exit_p = entry + (5 if i % 2 == 0 else -5)
        conn.execute(
            "INSERT INTO trade_log VALUES (?,?,?,?,?)",
            (entry, exit_p, i, i + 1, 1.0),
        )
    conn.commit()
    conn.close()


def test_train(tmp_path: Path) -> None:
    db = tmp_path / "trades.db"
    _create_db(db)
    model_path = tmp_path / "model.pkl"

    ml_trainer.DB_PATH = db
    ml_trainer.MODEL_PATH = model_path

    ml_trainer.train()
    assert model_path.exists()

    trades = ml_trainer._load_trades()
    features, labels = ml_trainer._build_features(trades)
    with model_path.open("rb") as f:
        clf = pickle.load(f)
    preds = clf.predict(features)
    assert len(preds) == len(labels)
