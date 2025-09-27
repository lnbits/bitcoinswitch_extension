from lnbits.db import Database

db = Database("ext_bitcoinswitch")


async def m001_initial(db):
    """
    Initial bitcoinswitch table.
    """
    await db.execute(
        f"""
        CREATE TABLE bitcoinswitch.switch (
            id TEXT NOT NULL PRIMARY KEY,
            key TEXT NOT NULL,
            title TEXT NOT NULL,
            wallet TEXT NOT NULL,
            currency TEXT NOT NULL,
            switches TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT {db.timestamp_now},
            updated_at TIMESTAMP NOT NULL DEFAULT {db.timestamp_now}
        );
    """
    )
    await db.execute(
        f"""
        CREATE TABLE bitcoinswitch.payment (
            id TEXT NOT NULL PRIMARY KEY,
            bitcoinswitch_id TEXT NOT NULL,
            payment_hash TEXT,
            payload TEXT NOT NULL,
            pin INT,
            sats {db.big_int},
            created_at TIMESTAMP NOT NULL DEFAULT {db.timestamp_now},
            updated_at TIMESTAMP NOT NULL DEFAULT {db.timestamp_now}
        );
    """
    )


async def m002_add_password(db):
    await db.execute(
        """
        ALTER TABLE bitcoinswitch.switch
        ADD COLUMN password TEXT;
        """
    )


async def m003_disabled(db):
    await db.execute(
        """
        ALTER TABLE bitcoinswitch.switch
        ADD COLUMN disabled BOOLEAN NOT NULL DEFAULT FALSE;
        """
    )


async def m004_disposable(db):
    await db.execute(
        """
        ALTER TABLE bitcoinswitch.switch
        ADD COLUMN disposable BOOLEAN NOT NULL DEFAULT TRUE;
        """
    )


async def m005_taproot_assets_support(db):
    """
    Add Taproot Assets support to payment table.
    """
    # Add basic taproot identification fields
    await db.execute(
        """
        ALTER TABLE bitcoinswitch.payment
        ADD COLUMN is_taproot BOOLEAN NOT NULL DEFAULT FALSE;
        """
    )

    await db.execute(
        """
        ALTER TABLE bitcoinswitch.payment
        ADD COLUMN asset_id TEXT;
        """
    )

    # Add market maker fields for rate tracking
    await db.execute(
        """
        ALTER TABLE bitcoinswitch.payment
        ADD COLUMN quoted_rate REAL;
        """
    )

    await db.execute(
        f"""
        ALTER TABLE bitcoinswitch.payment
        ADD COLUMN quoted_at TIMESTAMP;
        """
    )

    await db.execute(
        """
        ALTER TABLE bitcoinswitch.payment
        ADD COLUMN asset_amount INTEGER;
        """
    )

    # Add RFQ (Request for Quote) fields
    await db.execute(
        """
        ALTER TABLE bitcoinswitch.payment
        ADD COLUMN rfq_invoice_hash TEXT;
        """
    )

    await db.execute(
        """
        ALTER TABLE bitcoinswitch.payment
        ADD COLUMN rfq_asset_amount INTEGER;
        """
    )

    await db.execute(
        """
        ALTER TABLE bitcoinswitch.payment
        ADD COLUMN rfq_sat_amount REAL;
        """
    )
