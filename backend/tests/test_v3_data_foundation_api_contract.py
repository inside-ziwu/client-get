from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.ids import new_uuid
from app.main import create_app
from app.security.jwt import create_access_token
from app.services.keyword_service import get_or_create_keyword_master, normalize_keyword
from tests.helpers import make_engine


async def _create_tenant_and_token(slug: str) -> tuple[str, str]:
    tenant_id = str(new_uuid())
    user_id = str(new_uuid())
    engine = make_engine()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                INSERT INTO tenants (id, name, slug, industry, status, settings, needs_onboarding)
                VALUES (:tenant_id, :slug, :slug, 'PCB', 'active', '{}'::jsonb, false)
                """
            ),
            {"tenant_id": tenant_id, "slug": slug},
        )
        await conn.execute(
            text(
                """
                INSERT INTO users (id, tenant_id, email, password_hash, name, status, must_change_pwd)
                VALUES (:user_id, :tenant_id, :email, 'hash', '测试用户', 'active', false)
                """
            ),
            {"user_id": user_id, "tenant_id": tenant_id, "email": f"{slug}@example.com"},
        )
        await conn.execute(
            text(
                """
                INSERT INTO user_roles (id, tenant_id, user_id, role)
                VALUES (:id, :tenant_id, :user_id, 'admin')
                """
            ),
            {"id": str(new_uuid()), "tenant_id": tenant_id, "user_id": user_id},
        )
    await engine.dispose()
    return tenant_id, create_access_token(
        {
            "sub": user_id,
            "kind": "tenant",
            "tid": tenant_id,
            "slug": slug,
            "roles": ["admin"],
        }
    )


async def _create_platform_token() -> str:
    user_id = str(new_uuid())
    engine = make_engine()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                INSERT INTO platform_users (id, email, password_hash, name, status)
                VALUES (:id, :email, 'hash', '平台管理员', 'active')
                """
            ),
            {"id": user_id, "email": f"df-admin-{uuid4().hex[:8]}@example.com"},
        )
    await engine.dispose()
    return create_access_token({"sub": user_id, "kind": "platform", "roles": ["platform_admin"]})


async def _seed_visible_company(tenant_id: str) -> dict:
    engine = make_engine()
    async with engine.begin() as conn:
        keyword_master_id = await get_or_create_keyword_master(
            conn,
            keyword="P.C.B",
            keyword_normalized=normalize_keyword("P.C.B"),
        )
        await conn.execute(
            text(
                """
                INSERT INTO tenant_keyword (tenant_id, keyword_master_id, keyword_raw, status)
                VALUES (:tenant_id, :keyword_master_id, 'P.C.B', 'active')
                ON CONFLICT (tenant_id, keyword_master_id) DO UPDATE
                SET keyword_raw = EXCLUDED.keyword_raw,
                    status = 'active'
                """
            ),
            {"tenant_id": tenant_id, "keyword_master_id": keyword_master_id},
        )
        company_name = f"Alpha PCB {uuid4().hex[:8]}"
        sys_company_id = str(new_uuid())
        clean_company_id = (
            await conn.execute(
                text(
                    """
                    INSERT INTO clean_companies
                      (name, name_normalized, country_iso3, website, tax_no, incorporation_date,
                       reg_capital, employee_num, industry_desc, industry_tags, product_tags,
                       pcb_suppliers, trade_amount_3y_usd, trade_count, contacts_count)
                    VALUES
                      (:name, :name_normalized, 'USA', 'https://alpha.example', 'TAX-1', '2010-01-01',
                       1000000, '51-200', 'PCB importer', ARRAY['pcb_importer'], ARRAY['pcb'],
                       ARRAY['Supplier A'], 12345.67, 8, 1)
                    RETURNING id
                    """
                ),
                {"name": company_name, "name_normalized": f"alpha-{uuid4().hex}"},
            )
        ).scalar_one()
        wmt_company_id = (
            await conn.execute(
                text(
                    """
                    INSERT INTO waimaotong_clean_companies
                      (company_name, country_iso3, website, domain, industry, sub_industry,
                       employee_size, product_tags, data_source_tags,
                       trade_amount_3y_usd, trade_count, contacts_count, founded_year,
                       sys_company_id)
                    VALUES
                      (:company_name, 'USA', 'https://alpha.example', 'alpha.example',
                       'PCB importer', 'pcb_importer',
                       '51-200', ARRAY['pcb'], ARRAY['tendata'],
                       12345.67, 8, 1, 2010,
                       :sys_company_id)
                    RETURNING id
                    """
                ),
                {"company_name": company_name, "sys_company_id": sys_company_id},
            )
        ).scalar_one()
        await conn.execute(
            text(
                """
                INSERT INTO clean_company_keywords (clean_company_id, keyword_master_id)
                VALUES (:clean_company_id, :keyword_master_id)
                """
            ),
            {"clean_company_id": clean_company_id, "keyword_master_id": keyword_master_id},
        )
        tendata_company_id = (
            await conn.execute(
                text(
                    """
                    INSERT INTO tendata_raw_companies
                      (keyword_master_id, source_id, name, country_iso3, industry_desc,
                       product_tags, pcb_suppliers, trade_amount_3y_usd, trade_count,
                       contacts_count, raw_payload)
                    VALUES
                      (:keyword_master_id, :source_id, 'Alpha Raw', 'USA', 'PCB importer',
                       ARRAY['pcb'], ARRAY['Supplier A'], 12345.67, 8, 1, '{"secret": true}'::jsonb)
                    RETURNING id
                    """
                ),
                {"keyword_master_id": keyword_master_id, "source_id": f"td-{uuid4().hex}"},
            )
        ).scalar_one()
        await conn.execute(
            text(
                """
                INSERT INTO clean_company_sources
                  (clean_company_id, source_type, source_company_id, source_key)
                VALUES (:clean_company_id, 'tendata', :source_company_id, :source_key)
                """
            ),
            {
                "clean_company_id": clean_company_id,
                "source_company_id": tendata_company_id,
                "source_key": f"td-key-{uuid4().hex}",
            },
        )
        await conn.execute(
            text(
                """
                INSERT INTO tenant_companies
                  (tenant_id, clean_company_id, business_status, data_status, visibility_status, model_score, score, note, tags)
                VALUES
                  (:tenant_id, :clean_company_id, 'new', 'ready', 'visible', 88.5, 88.5, 'tenant note', ARRAY['hot'])
                """
            ),
            {"tenant_id": tenant_id, "clean_company_id": wmt_company_id},
        )
        clean_contact_id = (
            await conn.execute(
                text(
                    """
                    INSERT INTO clean_contacts (clean_company_id, name, position, email, phone)
                    VALUES (:clean_company_id, 'Jane Buyer', 'Purchasing Manager', 'jane@example.com', '+1-555')
                    RETURNING id
                    """
                ),
                {"clean_company_id": clean_company_id},
            )
        ).scalar_one()
        wmt_contact_id = (
            await conn.execute(
                text(
                    """
                    INSERT INTO waimaotong_clean_contacts
                      (sys_company_id, name, position, email, phone)
                    VALUES (:sys_company_id, 'Jane Buyer', 'Purchasing Manager', 'jane@example.com', '+1-555')
                    RETURNING id
                    """
                ),
                {"sys_company_id": sys_company_id},
            )
        ).scalar_one()
        await conn.execute(
            text(
                """
                INSERT INTO tenant_contacts
                  (tenant_id, clean_contact_id, clean_company_id, contact_status, is_sendable)
                VALUES (:tenant_id, :clean_contact_id, :clean_company_id, 'available', true)
                """
            ),
            {
                "tenant_id": tenant_id,
                "clean_contact_id": wmt_contact_id,
                "clean_company_id": wmt_company_id,
            },
        )
    await engine.dispose()
    return {
        "keyword_master_id": str(keyword_master_id),
        "clean_company_id": str(clean_company_id),
        "wmt_company_id": str(wmt_company_id),
        "tendata_company_id": str(tendata_company_id),
    }


async def test_tenant_company_detail_uses_clean_company_id_and_keyword_visibility() -> None:
    slug = f"df-api-{uuid4().hex[:8]}"
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            tenant_id, token = await _create_tenant_and_token(slug)
            seeded = await _seed_visible_company(tenant_id)
            response = await client.get(
                f"/t/{slug}/api/v1/companies/{seeded['wmt_company_id']}",
                headers={"Authorization": f"Bearer {token}"},
            )
            company_list = await client.get(
                f"/t/{slug}/api/v1/companies",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "source_type": "tendata",
                    "country_iso3": "USA",
                    "sub_industries[]": "pcb_importer",
                    "founded_year_from": 2000,
                    "product_tags[]": "pcb",
                    "employee_scale[]": "51-200",
                    "trade_amount_min": 1,
                    "trade_count_min": 1,
                    "contacts_count_min": 1,
                },
            )
            contacts = await client.get(
                f"/t/{slug}/api/v1/companies/{seeded['wmt_company_id']}/contacts",
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 200, response.text
    company = response.json()["data"]
    assert company["id"] == seeded["wmt_company_id"]
    assert company["tenant_state"]["business_status"] == "new"
    assert "tendata" in company["sources"]
    assert company["matched_keywords"] == []
    assert company_list.status_code == 200, company_list.text
    company_list_rows = company_list.json()["data"]
    assert any(item["id"] == seeded["wmt_company_id"] for item in company_list_rows)
    assert all("score_adjustment" not in item for item in company_list_rows)
    assert contacts.status_code == 200, contacts.text
    assert contacts.json()["data"][0]["email"] == "jane@example.com"
    assert contacts.json()["data"][0]["tenant_contact_state"]["is_sendable"] is True


async def test_tenant_companies_api_returns_cursor_when_more_rows_exist() -> None:
    slug = f"tenant-company-page-{uuid4().hex[:8]}"
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            tenant_id, token = await _create_tenant_and_token(slug)
            first = await _seed_visible_company(tenant_id)
            second = await _seed_visible_company(tenant_id)
            response = await client.get(
                f"/t/{slug}/api/v1/companies",
                headers={"Authorization": f"Bearer {token}"},
                params={"limit": 1},
            )
            next_response = await client.get(
                f"/t/{slug}/api/v1/companies",
                headers={"Authorization": f"Bearer {token}"},
                params={"limit": 1, "cursor": response.json()["pagination"]["cursor"]},
            )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert len(payload["data"]) == 1
    assert payload["pagination"]["has_more"] is True
    assert payload["pagination"]["cursor"] in {
        first["wmt_company_id"],
        second["wmt_company_id"],
    }
    assert payload["pagination"]["total"] == 2
    assert next_response.status_code == 200, next_response.text
    next_payload = next_response.json()
    assert len(next_payload["data"]) == 1
    assert next_payload["data"][0]["id"] != payload["data"][0]["id"]
    assert next_payload["pagination"]["has_more"] is False
    assert next_payload["pagination"]["cursor"] is None


async def test_tenant_companies_api_returns_page_pagination_total() -> None:
    slug = f"tenant-company-total-{uuid4().hex[:8]}"
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            tenant_id, token = await _create_tenant_and_token(slug)
            first = await _seed_visible_company(tenant_id)
            second = await _seed_visible_company(tenant_id)
            first_page = await client.get(
                f"/t/{slug}/api/v1/companies",
                headers={"Authorization": f"Bearer {token}"},
                params={"page": 1, "page_size": 1},
            )
            second_page = await client.get(
                f"/t/{slug}/api/v1/companies",
                headers={"Authorization": f"Bearer {token}"},
                params={"page": 2, "page_size": 1},
            )

    assert first_page.status_code == 200, first_page.text
    first_payload = first_page.json()
    assert len(first_payload["data"]) == 1
    assert first_payload["pagination"]["total"] == 2
    assert first_payload["pagination"]["has_more"] is True
    assert first_payload["data"][0]["id"] in {
        first["wmt_company_id"],
        second["wmt_company_id"],
    }

    assert second_page.status_code == 200, second_page.text
    second_payload = second_page.json()
    assert len(second_payload["data"]) == 1
    assert second_payload["pagination"]["total"] == 2
    assert second_payload["pagination"]["has_more"] is False
    assert second_payload["data"][0]["id"] != first_payload["data"][0]["id"]


async def test_tenant_companies_api_no_longer_accepts_grade_query_or_by_grade_stats() -> None:
    slug = f"tenant-no-grade-{uuid4().hex[:8]}"
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            _tenant_id, token = await _create_tenant_and_token(slug)
            headers = {"Authorization": f"Bearer {token}"}

            company_response = await client.get(
                f"/t/{slug}/api/v1/companies",
                headers=headers,
                params={"grade": "A"},
            )
            by_grade_response = await client.get(
                f"/t/{slug}/api/v1/emails/stats/by-grade",
                headers=headers,
            )

    assert company_response.status_code == 200, company_response.text
    assert by_grade_response.status_code == 404, by_grade_response.text


async def test_tenant_company_detail_rejects_invisible_clean_company() -> None:
    slug = f"df-api-hidden-{uuid4().hex[:8]}"
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            tenant_id, token = await _create_tenant_and_token(slug)
            seeded = await _seed_visible_company(tenant_id)
            engine = make_engine()
            async with engine.begin() as conn:
                await conn.execute(
                    text(
                        """
                        UPDATE tenant_keyword
                        SET status = 'deleted'
                        WHERE tenant_id = :tenant_id
                        """
                    ),
                    {"tenant_id": tenant_id},
                )
                await conn.execute(
                    text(
                        """
                        UPDATE tenant_companies
                        SET visibility_status = 'hidden'
                        WHERE tenant_id = :tenant_id
                          AND clean_company_id = :clean_company_id
                        """
                    ),
                    {"tenant_id": tenant_id, "clean_company_id": int(seeded["wmt_company_id"])},
                )
            await engine.dispose()
            response = await client.get(
                f"/t/{slug}/api/v1/companies/{seeded['wmt_company_id']}",
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 404, response.text


async def test_admin_raw_api_omits_raw_payload_by_default_and_clean_source_filter_uses_source_table() -> None:
    slug = f"df-admin-{uuid4().hex[:8]}"
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            tenant_id, _token = await _create_tenant_and_token(slug)
            seeded = await _seed_visible_company(tenant_id)
            admin_token = await _create_platform_token()
            raw_response = await client.get(
                "/admin/api/v1/raw/tendata/companies",
                headers={"Authorization": f"Bearer {admin_token}"},
                params={"keyword_master_id": seeded["keyword_master_id"], "page_size": 5},
            )
            clean_response = await client.get(
                "/admin/api/v1/clean/companies",
                headers={"Authorization": f"Bearer {admin_token}"},
                params={"source_type": "tendata", "page_size": 5},
            )

    assert raw_response.status_code == 200, raw_response.text
    assert raw_response.json()["data"]
    assert "raw_payload" not in raw_response.json()["data"][0]
    assert clean_response.status_code == 200, clean_response.text
    assert any(item["id"] == seeded["clean_company_id"] for item in clean_response.json()["data"])


async def test_admin_v3_data_pages_filters_use_contract_routes() -> None:
    slug = f"df-admin-pages-{uuid4().hex[:8]}"
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            tenant_id, _token = await _create_tenant_and_token(slug)
            seeded = await _seed_visible_company(tenant_id)
            admin_token = await _create_platform_token()
            engine = make_engine()
            async with engine.begin() as conn:
                await conn.execute(
                    text(
                        """
                        INSERT INTO lixiaoyun_api_companies
                          (keyword_master_id, pid, entname, entname_eng, official_website,
                           esdate, reg_cap, scale, regccap, annual_turnover, legalperson,
                           geo_address, dom, collected_at)
                        VALUES
                          (:keyword_master_id, :pid, '深圳同行 PCB', 'Peer PCB Ltd',
                           'peer.example', 1514808000000, '500万元', '50-200人',
                           '100万人民币', '1000万', '李法人', '深圳通讯地址', '深圳注册地址', now())
                        """
                    ),
                    {
                        "keyword_master_id": seeded["keyword_master_id"],
                        "pid": f"lxy-{uuid4().hex}",
                    },
                )
            await engine.dispose()

            lxy_response = await client.get(
                "/admin/api/v1/raw/lixiaoyun/companies",
                headers={"Authorization": f"Bearer {admin_token}"},
                params={
                    "q": "深圳同行",
                    "keyword_filter": "pcb",
                    "found_date_start": "2017-01-01",
                    "found_date_end": "2019-01-01",
                    "reg_capital": "500_2000",
                    "employee_scale": "50_200",
                    "has_name_en": True,
                    "has_domain": True,
                    "page_size": 5,
                },
            )
            tendata_response = await client.get(
                "/admin/api/v1/raw/tendata/companies",
                headers={"Authorization": f"Bearer {admin_token}"},
                params={
                    "q": "Alpha Raw",
                    "country_iso3": "USA",
                    "industry": "PCB",
                    "tag": "pcb",
                    "amount_min": 1,
                    "count_min": 1,
                    "pcb": "yes",
                    "contact_min": 1,
                    "page_size": 5,
                },
            )
            clean_response = await client.get(
                "/admin/api/v1/clean/companies",
                headers={"Authorization": f"Bearer {admin_token}"},
                params={
                    "source_type": "tendata",
                    "keyword": "Alpha",
                    "country_iso3": "USA",
                    "industry": "PCB",
                    "tag": "pcb",
                    "amount_min": 1,
                    "count_min": 1,
                    "pcb": "yes",
                    "contact_min": 1,
                    "page_size": 5,
                },
            )

    assert lxy_response.status_code == 200, lxy_response.text
    lxy_rows = lxy_response.json()["data"]
    assert lxy_rows[0]["entname"] == "深圳同行 PCB"
    assert lxy_rows[0]["entname_eng"] == "Peer PCB Ltd"
    assert lxy_rows[0]["official_website"] == "peer.example"
    assert lxy_rows[0]["keyword"] == "P.C.B"
    assert "raw_payload" not in lxy_rows[0]
    assert tendata_response.status_code == 200, tendata_response.text
    tendata_rows = tendata_response.json()["data"]
    assert any(item["id"] == seeded["tendata_company_id"] for item in tendata_rows)
    assert "raw_payload" not in tendata_rows[0]
    assert clean_response.status_code == 200, clean_response.text
    clean_rows = clean_response.json()["data"]
    assert any(item["id"] == seeded["clean_company_id"] for item in clean_rows)
    assert clean_rows[0]["sources"]


async def test_admin_lixiaoyun_raw_companies_reads_api_company_fields() -> None:
    slug = f"df-admin-lxy-api-{uuid4().hex[:8]}"
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            tenant_id, _token = await _create_tenant_and_token(slug)
            seeded = await _seed_visible_company(tenant_id)
            admin_token = await _create_platform_token()
            pid = f"lxy-api-{uuid4().hex}"
            engine = make_engine()
            async with engine.begin() as conn:
                await conn.execute(
                    text(
                        """
                        INSERT INTO lixiaoyun_api_companies
                          (keyword_master_id, pid, entname, entname_eng, official_website,
                           esdate, reg_cap, regccap, scale, annual_turnover, legalperson,
                           geo_address, dom, collected_at)
                        VALUES
                          (
                            :keyword_master_id,
                            :pid,
                            '深圳API同行',
                            'API Peer PCB Ltd',
                            'api-peer.example',
                            1514808000000,
                            '500万元',
                            '100万人民币',
                            '50-200人',
                            '1000万',
                            '张法人',
                            '深圳通讯地址',
                            '深圳注册地址',
                            now()
                          )
                        """
                    ),
                    {
                        "keyword_master_id": seeded["keyword_master_id"],
                        "pid": pid,
                    },
                )
            await engine.dispose()

            response = await client.get(
                "/admin/api/v1/raw/lixiaoyun/companies",
                headers={"Authorization": f"Bearer {admin_token}"},
                params={"q": "深圳API同行", "page_size": 5},
            )

    assert response.status_code == 200, response.text
    rows = response.json()["data"]
    row = next(item for item in rows if item["pid"] == pid)
    assert row["entname"] == "深圳API同行"
    assert row["entname_eng"] == "API Peer PCB Ltd"
    assert row["official_website"] == "api-peer.example"
    assert row["reg_cap"] == "500万元"
    assert row["regccap"] == "100万人民币"
    assert row["scale"] == "50-200人"
    assert row["annual_turnover"] == "1000万"
    assert row["legalperson"] == "张法人"
    assert row["geo_address"] == "深圳通讯地址"
    assert row["dom"] == "深圳注册地址"
    assert row["keyword"] == "P.C.B"
    assert "raw_payload" not in row


async def test_admin_lixiaoyun_raw_company_contacts_route_is_temporarily_empty() -> None:
    slug = f"df-admin-lxy-contacts-{uuid4().hex[:8]}"
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            tenant_id, _token = await _create_tenant_and_token(slug)
            seeded = await _seed_visible_company(tenant_id)
            admin_token = await _create_platform_token()
            engine = make_engine()
            async with engine.begin() as conn:
                lxy_company_id = (
                    await conn.execute(
                        text(
                            """
                            INSERT INTO lixiaoyun_api_companies
                              (keyword_master_id, pid, entname, collected_at)
                            VALUES
                              (:keyword_master_id, :pid, '深圳同行联系人', now())
                            RETURNING id
                            """
                        ),
                        {
                            "keyword_master_id": seeded["keyword_master_id"],
                            "pid": f"lxy-contact-{uuid4().hex}",
                        },
                    )
                ).scalar_one()
            await engine.dispose()

            response = await client.get(
                f"/admin/api/v1/raw/lixiaoyun/companies/{lxy_company_id}/contacts",
                headers={"Authorization": f"Bearer {admin_token}"},
            )

    assert response.status_code == 200, response.text
    rows = response.json()["data"]
    assert rows == []


async def test_admin_tendata_raw_company_contacts_route_returns_contact_rows() -> None:
    slug = f"df-admin-td-contacts-{uuid4().hex[:8]}"
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            tenant_id, _token = await _create_tenant_and_token(slug)
            seeded = await _seed_visible_company(tenant_id)
            admin_token = await _create_platform_token()
            engine = make_engine()
            async with engine.begin() as conn:
                tendata_company_id = (
                    await conn.execute(
                        text(
                            """
                            INSERT INTO tendata_raw_companies
                              (keyword_master_id, source_id, collection_type, name, raw_payload)
                            VALUES
                              (:keyword_master_id, :source_id, 'reverse_lookup',
                               'Tendata Buyer With Contacts', '{}'::jsonb)
                            RETURNING id
                            """
                        ),
                        {
                            "keyword_master_id": seeded["keyword_master_id"],
                            "source_id": f"td-contact-{uuid4().hex}",
                        },
                    )
                ).scalar_one()
                await conn.execute(
                    text(
                        """
                        INSERT INTO tendata_raw_contacts
                          (raw_company_id, source_contact_id, name, position, email, phone, raw_payload)
                        VALUES
                          (:raw_company_id, 'tdc-1', 'Ada Buyer', 'Procurement Director',
                           'ada@example.com', '+1-202', '{"mobile": "+1-303"}'::jsonb)
                        """
                    ),
                    {"raw_company_id": tendata_company_id},
                )
            await engine.dispose()

            response = await client.get(
                f"/admin/api/v1/raw/tendata/companies/{tendata_company_id}/contacts",
                headers={"Authorization": f"Bearer {admin_token}"},
            )

    assert response.status_code == 200, response.text
    rows = response.json()["data"]
    assert rows == [
        {
            "id": rows[0]["id"],
            "raw_company_id": str(tendata_company_id),
            "source_contact_id": "tdc-1",
            "name": "Ada Buyer",
            "position": "Procurement Director",
            "email": "ada@example.com",
            "phone": "+1-202",
            "mobile": "+1-303",
            "created_at": rows[0]["created_at"],
        }
    ]
    assert "raw_payload" not in rows[0]
