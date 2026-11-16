
# =====================================================
# WEBEOUT — DATABASE SYSTEM
# SQLite + suporte a fontes externas e afiliados
# =====================================================

import sqlite3
from pathlib import Path
from datetime import datetime, timezone


DATABASE_PATH = Path(__file__).resolve().parent / "webeout.db"


def current_timestamp():
    return datetime.now(timezone.utc).isoformat()


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


# =====================================================
# CRIAR E ATUALIZAR ESTRUTURA DO BANCO
# =====================================================

def initialize_database():

    with get_connection() as connection:

        # 1. Cria as tabelas básicas.
        # Não cria índices de colunas novas aqui.

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
                created_at TEXT NOT NULL

            );


            CREATE TABLE IF NOT EXISTS price_history (

                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,

                price REAL NOT NULL
                    CHECK (price > 0),

                currency TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                source TEXT,

                FOREIGN KEY (product_id)
                    REFERENCES products(id)
                    ON DELETE CASCADE

            );

        """)

        # 2. Identifica as colunas que já existem.

        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(products)"
            ).fetchall()
        }

        # 3. Adiciona as novas colunas sem apagar os dados.

        migrations = {
            "affiliate_url": "TEXT",
            "external_id": "TEXT",
            "catalog_source": "TEXT",
            "last_seen_at": "TEXT",
            "is_active": "INTEGER NOT NULL DEFAULT 1"
        }

        for column, definition in migrations.items():

            if column not in columns:

                connection.execute(
                    f"ALTER TABLE products ADD COLUMN {column} {definition}"
                )

        # 4. Agora que as colunas existem, cria os índices.

        connection.executescript("""

            CREATE INDEX IF NOT EXISTS idx_price_product
            ON price_history(product_id);

            CREATE INDEX IF NOT EXISTS idx_price_date
            ON price_history(recorded_at);

            CREATE INDEX IF NOT EXISTS idx_product_market
            ON products(market);

            CREATE INDEX IF NOT EXISTS idx_product_external
            ON products(external_id);

        """)

    print("Webeout database initialized successfully.")


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
                    excluded.category,
                    products.category
                ),

                store = COALESCE(
                    excluded.store,
                    products.store
                ),

                product_url = COALESCE(
                    excluded.product_url,
                    products.product_url
                ),

                image_url = COALESCE(
                    excluded.image_url,
                    products.image_url
                ),

                affiliate_url = COALESCE(
                    excluded.affiliate_url,
                    products.affiliate_url
                ),

                external_id = COALESCE(
                    excluded.external_id,
                    products.external_id
                ),

                catalog_source = COALESCE(
                    excluded.catalog_source,
                    products.catalog_source
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
# REGISTRAR PREÇO
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
                source
            )

            VALUES (?, ?, ?, ?, ?)

        """, (
            product_id,
            round(price, 2),
            currency,
            current_timestamp(),
            source
        ))

        return cursor.lastrowid


# =====================================================
# CONSULTAR HISTÓRICO DE PREÇOS
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

            ORDER BY recorded_at ASC

        """, (product_id,)).fetchall()

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
# TESTE SEGURO
# =====================================================

if __name__ == "__main__":

    initialize_database()

    print("\nPRODUCTS:")
    print(get_products("US"))

    print("\nDatabase test completed.")
