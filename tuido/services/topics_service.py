import logging

from termz.util.datetime import today_date  # type: ignore

from tuido.domain.models import FieldDefinition
from tuido.services.config_service import ConfigService
from tuido.storage.topics.base import BaseTopicRepository


class TopicsService:
    """
    Business logic for topic management.

    Owns the in-memory topics list and delegates persistence to the
    injected repository.
    """

    _repo: BaseTopicRepository
    _config: ConfigService
    _data: list[dict]
    _topics_by_id: dict[int, dict]


    def __init__(
        self, repo: BaseTopicRepository, config: ConfigService
    ) -> None:
        self._repo = repo
        self._config = config
        self._data = []
        self._topics_by_id = {}
        self._load()

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def get_all_topics(self) -> list[dict]:
        """Return the full in-memory topics list."""
        return self._data

    def get_topic_by_id(self, topic_id: int) -> dict:
        """Return a single topic dict by ID."""
        return self._topics_by_id[topic_id]

    def create_topic(self) -> dict:
        """
        Create a new empty topic, persist it, and return it.

        The new topic gets the next available integer ID and has all
        configured field functions applied (e.g. 'created_date').
        """
        new_id = max((t['id'] for t in self._data), default=0) + 1
        new_topic: dict = {'id': new_id}
        for col in self._config.get_columns():
            new_topic[col.name] = ''
        new_topic = self._apply_field_functions(new_topic, action='new')
        self._data.append(new_topic)
        self._topics_by_id[new_id] = new_topic
        self._save()
        logging.info(f'TopicsService: created topic id={new_id}.')
        return new_topic

    def update_topic(
        self, topic_id: int, updated_topic: dict
    ) -> dict:
        """
        Update a topic, apply field functions and persist.

        Returns the final updated topic dict.
        """
        old = self._topics_by_id.get(topic_id)
        if old is None:
            logging.warning(f'TopicsService: topic {topic_id} not found.')
            return updated_topic
        self._data.remove(old)
        updated_topic = self._apply_field_functions(updated_topic, action='edit')
        self._data.append(updated_topic)
        self._topics_by_id[topic_id] = updated_topic
        self._save()
        logging.info(f'TopicsService: updated topic id={topic_id}.')
        return updated_topic

    def delete_topic(self, topic_id: int) -> None:
        """Remove a topic by ID and persist."""
        topic = self._topics_by_id.pop(topic_id, None)
        if topic:
            self._data.remove(topic)
            self._save()
        logging.info(f'TopicsService: deleted topic id={topic_id}.')

    # ------------------------------------------------------------------ #
    #  Private helpers                                                     #
    # ------------------------------------------------------------------ #

    def _load(self) -> None:
        self._data = self._repo.load()
        for topic in self._data:
            tid = topic.get('id')
            if tid is not None:
                self._topics_by_id[int(tid)] = topic
        logging.info(f'TopicsService: loaded {len(self._data)} topics.')

    def _save(self) -> None:
        self._repo.save(self._data)
        logging.info('TopicsService: topics saved.')

    def _apply_field_functions(
        self, topic: dict, action: str
    ) -> dict:
        """Apply 'created_date' / 'edit_date' computed fields."""
        today = today_date(english_format=True)
        columns_dict: dict[str, FieldDefinition] = \
            self._config.get_columns_dict()

        for field_name, field_def in columns_dict.items():
            match field_def.computed:
                case 'created_date':
                    if action == 'new':
                        topic[field_name] = today
                case 'edit_date':
                    topic[field_name] = today
        return topic
