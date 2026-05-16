from app.core.errors import AppError
from app.integrations.collection.base import CollectionPayload, CollectionProvider, CollectionTask
from app.integrations.collection.lixiaoyun import LixiaoyunCollectionProvider
from app.integrations.collection.tendata import TendataCollectionProvider
from app.integrations.collection.waimaotong import WaiMaoTongCollectionProvider


class CollectionProviderRouter:
    def __init__(
        self,
        providers: dict[str, CollectionProvider] | None = None,
        credentials_by_source: dict[str, list[dict]] | None = None,
    ) -> None:
        if providers is not None:
            self.providers = providers
        else:
            creds = credentials_by_source or {}
            self.providers = {
                WaiMaoTongCollectionProvider.source_type: WaiMaoTongCollectionProvider(
                    creds.get(WaiMaoTongCollectionProvider.source_type, [])
                ),
                TendataCollectionProvider.source_type: TendataCollectionProvider(
                    creds.get(TendataCollectionProvider.source_type, [])
                ),
                LixiaoyunCollectionProvider.source_type: LixiaoyunCollectionProvider(
                    creds.get(LixiaoyunCollectionProvider.source_type, [])
                ),
            }

    async def collect(self, task: CollectionTask) -> CollectionPayload:
        payload = CollectionPayload()
        for source_type in task.source_types:
            provider = self.providers.get(source_type)
            if provider is None:
                raise AppError(
                    code="COLLECTION_PROVIDER_UNSUPPORTED",
                    message=f"未找到采集源 {source_type} 的 provider",
                    status_code=422,
                )
            result = await provider.collect(task)
            payload.companies.extend(result.companies)
            payload.contacts.extend(result.contacts)
            payload.competitors.extend(result.competitors)
        return payload
