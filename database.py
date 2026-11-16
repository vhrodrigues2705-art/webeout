
# =====================================================
# WEBEOUT — DATABASE SYSTEM
# PostgreSQL (Neon) + SQLite (local)
# Products + Offers + Independent Price History
# =====================================================

import os
import sqlite3
import hashlib

from pathlib import Path
from datetime import datetime, timezone


DATABASE_PATH = Path(__file__).resolve().parent / "webeout.db"
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

USE_POSTGRES = DATABASE_URL.startswith(
    ("postgresql://", "postgres://")
)


def current_timestamp():
    return datetime.now(timezone.utc).isoformat()


# =====================================================
# CONEXÃO
# =====================================================

class DatabaseConnection:

    def __init__(self, connection, postgres=False):
        self.connection = connection
        self.postgres = postgres

    def execute(self, query, parameters=()):
        if self.postgres:
            query = query.replace("?", "%s")

        return self.connection.execute(query, parameters)

    def executescript(self, script):
        if self.postgres:
            for statement in script.split(";"):
                statement = statement.strip()
                if statement:
                    self.connection.execute(statement)
        else:
            self.connection.executescript(script)

    def __enter__(self):
        self.connection.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self.connection.__exit__(
            exc_type, exc_value, traceback
        )


def get_connection():

    if USE_POSTGRES:
        import psycopg
        from psycopg.rows import dict_row

        connection = psycopg.connect(
            DATABASE_URL,
            row_factory=dict_row,
            connect_timeout=15
        )

        return DatabaseConnection(connection, postgres=True)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return DatabaseConnection(connection)


# =====================================================
# CRIAR E ATUALIZAR ESTRUTURA
# =====================================================

def initialize_database():

    with get_connection() as connection:

        if USE_POSTGRES:

            connection.executescript("""
                CREATE TABLE IF NOT EXISTS products (
                    id BIGSERIAL PRIMARY KEY,
                    product_code TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    category TEXT,
                    market TEXT NOT NULL
                        CHECK (market IN ('US', 'DE')),
                    currency TEXT NOT NULL
                        CHECK (currency IN ('USD', 'EUR')),
                    store TEXT,
                    product_url TEXT,
                    image_url TEXT,
                    created_at TEXT NOT NULL,
                    affiliate_url TEXT,
                    external_id TEXT,
                    catalog_source TEXT,
                    last_seen_at TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS offers (
                    id BIGSERIAL PRIMARY KEY,
                    offer_code TEXT NOT NULL UNIQUE,
                    product_id BIGINT NOT NULL,
                    store TEXT NOT NULL,
                    external_id TEXT,
                    product_url TEXT,
                    affiliate_url TEXT,
                    image_url TEXT,
                    catalog_source TEXT,
                    created_at TEXT NOT NULL,
                    last_seen_at TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    FOREIGN KEY (product_id)
                        REFERENCES products(id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS price_history (
                    id BIGSERIAL PRIMARY KEY,
                    product_id BIGINT NOT NULL,
                    price DOUBLE PRECISION NOT NULL
                        CHECK (price > 0),
                    currency TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    source TEXT,
                    offer_id BIGINT,
                    FOREIGN KEY (product_id)
                        REFERENCES products(id)
                        ON DELETE CASCADE,
                    FOREIGN KEY (offer_id)
                        REFERENCES offers(id)
                        ON DELETE CASCADE
                );
            """)

            # Migrações seguras para bancos existentes.

            connection.executescript("""
                ALTER TABLE products
                    ADD COLUMN IF NOT EXISTS affiliate_url TEXT;

                ALTER TABLE products
                    ADD COLUMN IF NOT EXISTS external_id TEXT;

                ALTER TABLE products
                    ADD COLUMN IF NOT EXISTS catalog_source TEXT;

                ALTER TABLE products
                    ADD COLUMN IF NOT EXISTS last_seen_at TEXT;

                ALTER TABLE products
                    ADD COLUMN IF NOT EXISTS is_active INTEGER
                    NOT NULL DEFAULT 1;

                ALTER TABLE price_history
                    ADD COLUMN IF NOT EXISTS offer_id BIGINT;
            """)

            connection.executescript("""
                CREATE INDEX IF NOT EXISTS idx_price_product
                    ON price_history(product_id);

                CREATE INDEX IF NOT EXISTS idx_price_date
                    ON price_history(recorded_at);

                CREATE INDEX IF NOT EXISTS idx_price_offer
                    ON price_history(offer_id);

                CREATE INDEX IF NOT EXISTS idx_product_market
                    ON products(market);

                CREATE INDEX IF NOT EXISTS idx_product_external
                    ON products(external_id);

                CREATE INDEX IF NOT EXISTS idx_offer_product
                    ON offers(product_id);

                CREATE INDEX IF NOT EXISTS idx_offer_external
                    ON offers(external_id);
            """)

        else:

            connection.executescript("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_code TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    category TEXT,
                    market TEXT NOT NULL
                        CHECK (market IN ('US', 'DE')),
                    currency TEXT NOT NULL
                        CHECK (currency IN ('USD', 'EUR')),
                    store TEXT,
                    product_url TEXT,
                    image_url TEXT,
                    created_at TEXT NOT NULL,
                    affiliate_url TEXT,
                    external_id TEXT,
                    catalog_source TEXT,
                    last_seen_at TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS offers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    offer_code TEXT NOT NULL UNIQUE,
                    product_id INTEGER NOT NULL,
                    store TEXT NOT NULL,
                    external_id TEXT,
                    product_url TEXT,
                    affiliate_url TEXT,
                    image_url TEXT,
                    catalog_source TEXT,
                    created_at TEXT NOT NULL,
                    last_seen_at TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    FOREIGN KEY (product_id)
                        REFERENCES products(id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    price REAL NOT NULL CHECK (price > 0),
                    currency TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    source TEXT,
                    offer_id INTEGER,
                    FOREIGN KEY (product_id)
                        REFERENCES products(id)
                        ON DELETE CASCADE,
                    FOREIGN KEY (offer_id)
                        REFERENCES offers(id)
                        ON DELETE CASCADE
                );
            """)

            # Verificar colunas existentes.

            product_columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(products)"
                ).fetchall()
            }

            product_migrations = {
                "affiliate_url": "TEXT",
                "external_id": "TEXT",
                "catalog_source": "TEXT",
                "last_seen_at": "TEXT",
                "is_active": "INTEGER NOT NULL DEFAULT 1"
            }

            for column, definition in product_migrations.items():
                if column not in product_columns:
                    connection.execute(
                        f"ALTER TABLE products "
                        f"ADD COLUMN {column} {definition}"
                    )

            price_columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(price_history)"
                ).fetchall()
            }

            if "offer_id" not in price_columns:
                connection.execute(
                    "ALTER TABLE price_history ADD COLUMN offer_id INTEGER"
                )

            connection.executescript("""
                CREATE INDEX IF NOT EXISTS idx_price_product
                    ON price_history(product_id);

                CREATE INDEX IF NOT EXISTS idx_price_date
                    ON price_history(recorded_at);

                CREATE INDEX IF NOT EXISTS idx_price_offer
                    ON price_history(offer_id);

                CREATE INDEX IF NOT EXISTS idx_product_market
                    ON products(market);

                CREATE INDEX IF NOT EXISTS idx_product_external
                    ON products(external_id);

                CREATE INDEX IF NOT EXISTS idx_offer_product
                    ON offers(product_id);

                CREATE INDEX IF NOT EXISTS idx_offer_external
                    ON offers(external_id);
            """)

    print(
        "Webeout PostgreSQL database initialized successfully."
        if USE_POSTGRES
        else "Webeout SQLite database initialized successfully."
    )


# =====================================================
# CADASTRAR OU ATUALIZAR PRODUTO
# =====================================================

def add_product(
    product_code,
    name,
    category,
    market,
    currency,
    store=None,
    product_url=None,
    image_url=None,
    affiliate_url=None,
    external_id=None,
    catalog_source=None
):

    if not product_code or not name:
        raise ValueError("Product code and name are required.")

    if market not in ("US", "DE"):
        raise ValueError("Unsupported market.")

    expected_currency = {
        "US": "USD",
        "DE": "EUR"
    }[market]

    if currency != expected_currency:
        raise ValueError("Currency does not match market.")

    timestamp = current_timestamp()

    with get_connection() as connection:

        connection.execute("""
            INSERT INTO products (
                product_code,
                name,
                category,
                market,
                currency,
                store,
                product_url,
                image_url,
                affiliate_url,
                external_id,
                catalog_source,
                last_seen_at,
                is_active,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)

            ON CONFLICT(product_code) DO UPDATE SET
                name = excluded.name,
                category = COALESCE(
                    excluded.category, products.category
                ),
                store = COALESCE(
                    excluded.store, products.store
                ),
                product_url = COALESCE(
                    excluded.product_url, products.product_url
                ),
                image_url = COALESCE(
                    excluded.image_url, products.image_url
                ),
                affiliate_url = COALESCE(
                    excluded.affiliate_url, products.affiliate_url
                ),
                external_id = COALESCE(
                    excluded.external_id, products.external_id
                ),
                catalog_source = COALESCE(
                    excluded.catalog_source, products.catalog_source
                ),
                last_seen_at = excluded.last_seen_at,
                is_active = 1
        """, (
            product_code,
            name,
            category,
            market,
            currency,
            store,
            product_url,
            image_url,
            affiliate_url,
            external_id,
            catalog_source,
            timestamp,
            timestamp
        ))

        row = connection.execute(
            "SELECT id FROM products WHERE product_code = ?",
            (product_code,)
        ).fetchone()

        return row["id"]


# =====================================================
# CADASTRAR OU ATUALIZAR OFERTA
# =====================================================

def add_offer(
    product_id,
    store,
    external_id=None,
    product_url=None,
    affiliate_url=None,
    image_url=None,
    catalog_source=None
):

    if not store or not str(store).strip():
        raise ValueError("Offer store is required.")

    store = str(store).strip()

    # Identidade estável da oferta.
    identity = external_id or product_url or store

    raw_code = (
        f"{product_id}|{store.lower()}|{identity}"
    )

    offer_code = hashlib.sha256(
        raw_code.encode("utf-8")
    ).hexdigest()

    timestamp = current_timestamp()

    with get_connection() as connection:

        product = connection.execute(
            "SELECT id FROM products WHERE id = ?",
            (product_id,)
        ).fetchone()

        if product is None:
            raise ValueError("Product not found.")

        connection.execute("""
            INSERT INTO offers (
                offer_code,
                product_id,
                store,
                external_id,
                product_url,
                affiliate_url,
                image_url,
                catalog_source,
                created_at,
                last_seen_at,
                is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)

            ON CONFLICT(offer_code) DO UPDATE SET
                store = excluded.store,
                external_id = COALESCE(
                    excluded.external_id, offers.external_id
                ),
                product_url = COALESCE(
                    excluded.product_url, offers.product_url
                ),
                affiliate_url = COALESCE(
                    excluded.affiliate_url, offers.affiliate_url
                ),
                image_url = COALESCE(
                    excluded.image_url, offers.image_url
                ),
                catalog_source = COALESCE(
                    excluded.catalog_source, offers.catalog_source
                ),
                last_seen_at = excluded.last_seen_at,
                is_active = 1
        """, (
            offer_code,
            product_id,
            store,
            external_id,
            product_url,
            affiliate_url,
            image_url,
            catalog_source,
            timestamp,
            timestamp
        ))

        row = connection.execute(
            "SELECT id FROM offers WHERE offer_code = ?",
            (offer_code,)
        ).fetchone()

        return row["id"]


# =====================================================
# REGISTRAR PREÇO LEGADO (POR PRODUTO)
# Mantido para compatibilidade com a API atual.
# =====================================================

def add_price(product_id, price, currency, source=None):

    price = float(price)

    if price <= 0:
        raise ValueError("Price must be greater than zero.")

    with get_connection() as connection:

        product = connection.execute(
            "SELECT currency FROM products WHERE id = ?",
            (product_id,)
        ).fetchone()

        if product is None:
            raise ValueError("Product not found.")

        if product["currency"] != currency:
            raise ValueError("Currency does not match product.")

        cursor = connection.execute("""
            INSERT INTO price_history (
                product_id,
                price,
                currency,
                recorded_at,
                source,
                offer_id
            )
            VALUES (?, ?, ?, ?, ?, NULL)
            RETURNING id
        """, (
            product_id,
            round(price, 2),
            currency,
            current_timestamp(),
            source
        ))

        return cursor.fetchone()["id"]


# =====================================================
# REGISTRAR PREÇO DE UMA OFERTA ESPECÍFICA
# =====================================================

def add_offer_price(offer_id, price, currency, source=None):

    price = float(price)

    if price <= 0:
        raise ValueError("Price must be greater than zero.")

    with get_connection() as connection:

        offer = connection.execute("""
            SELECT
                offers.id,
                offers.product_id,
                products.currency
            FROM offers
            JOIN products
                ON products.id = offers.product_id
            WHERE offers.id = ?
        """, (offer_id,)).fetchone()

        if offer is None:
            raise ValueError("Offer not found.")

        if offer["currency"] != currency:
            raise ValueError("Currency does not match product.")

        cursor = connection.execute("""
            INSERT INTO price_history (
                product_id,
                price,
                currency,
                recorded_at,
                source,
                offer_id
            )
            VALUES (?, ?, ?, ?, ?, ?)
            RETURNING id
        """, (
            offer["product_id"],
            round(price, 2),
            currency,
            current_timestamp(),
            source,
            offer_id
        ))

        return cursor.fetchone()["id"]


# =====================================================
# CONSULTAR HISTÓRICO LEGADO POR PRODUTO
# =====================================================

def get_price_history(product_id):

    with get_connection() as connection:

        rows = connection.execute("""
            SELECT
                price,
                currency,
                recorded_at,
                source
            FROM price_history
            WHERE product_id = ?
            ORDER BY recorded_at ASC, id ASC
        """, (product_id,)).fetchall()

        return [dict(row) for row in rows]


# =====================================================
# CONSULTAR HISTÓRICO DE UMA OFERTA
# =====================================================

def get_offer_history(offer_id):

    with get_connection() as connection:

        rows = connection.execute("""
            SELECT
                price,
                currency,
                recorded_at,
                source,
                offer_id
            FROM price_history
            WHERE offer_id = ?
            ORDER BY recorded_at ASC, id ASC
        """, (offer_id,)).fetchall()

        return [dict(row) for row in rows]


# =====================================================
# LISTAR OFERTAS
# =====================================================

def get_offers(product_id=None, market=None):

    query = """
        SELECT
            offers.*,
            products.product_code,
            products.name,
            products.category,
            products.market,
            products.currency
        FROM offers
        JOIN products
            ON products.id = offers.product_id
        WHERE offers.is_active = 1
          AND products.is_active = 1
    """

    parameters = []

    if product_id is not None:
        query += " AND offers.product_id = ?"
        parameters.append(product_id)

    if market is not None:
        query += " AND products.market = ?"
        parameters.append(market)

    query += " ORDER BY offers.created_at DESC"

    with get_connection() as connection:

        rows = connection.execute(
            query, tuple(parameters)
        ).fetchall()

        return [dict(row) for row in rows]


# =====================================================
# LISTAR PRODUTOS
# =====================================================

def get_products(market=None):

    with get_connection() as connection:

        if market is None:
            rows = connection.execute("""
                SELECT *
                FROM products
                ORDER BY created_at DESC
            """).fetchall()

        else:
            rows = connection.execute("""
                SELECT *
                FROM products
                WHERE market = ?
                ORDER BY created_at DESC
            """, (market,)).fetchall()

        return [dict(row) for row in rows]


# =====================================================
# DESATIVAR PRODUTO
# =====================================================

def deactivate_product(product_code):

    with get_connection() as connection:

        cursor = connection.execute("""
            UPDATE products
            SET is_active = 0
            WHERE product_code = ?
        """, (product_code,))

        return cursor.rowcount > 0


# =====================================================
# DESATIVAR OFERTA
# =====================================================

def deactivate_offer(offer_id):

    with get_connection() as connection:

        cursor = connection.execute("""
            UPDATE offers
            SET is_active = 0
            WHERE id = ?
        """, (offer_id,))

        return cursor.rowcount > 0


# =====================================================
# TESTE
# =====================================================

if __name__ == "__main__":

    initialize_database()

    print("\nPRODUCTS:")
    print(get_products("US"))

    print("\nOFFERS:")
    print(get_offers(market="US"))

    print("\nDatabase test completed.")
