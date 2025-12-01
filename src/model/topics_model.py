import logging
import json
import os

from pylightlib.msc.Singleton import Singleton  # type: ignore


class Topic(metaclass=Singleton):
    """
    Model for the topics.

    Attributes
    ----------
    json_path : str
        The path to the JSON file containing the topics data.
    data : list[dict[str, str | int | float | bool]]
        The data loaded from the JSON file.
    topics_by_id : dict[int, dict[str, str | int | float | bool]]
        A dictionary mapping topic IDs to their data.
    """
    json_path: str
    data: list[dict[str, str | int | float | bool]] = []
    topics_by_id: dict[int, dict[str, str | int | float | bool]] = {}


    def __init__(self, json_path: str):
        """
        Initializes the Topic model.

        Parameters
        ----------
        json_path : str
            The path to the JSON file containing the topics data.
        """
        self.json_path = json_path
        self.load_from_file()
        self.set_default_values()
        self.create_topics_by_id_dict()

    def load_from_file(self) -> None:
        """
        Loads the topics from a JSON file.
        """
        # Check if json file exists
        json_path = self.json_path
        if not os.path.exists(json_path):
            if not os.path.exists(f'../{json_path}'):
                # TODO: Create a new file instead of raising an error
                raise FileNotFoundError(
                    f'Topics file "{json_path}" not found.')
            else:
                json_path = f'../{json_path}'

        # Load the JSON data
        with open(json_path, 'r', encoding='utf-8') as file:
            self.data = json.load(file)

        logging.info(f'Loaded {len(self.data)} topics from {json_path}.')

    # TODO: Clean up
    def set_default_values(self) -> None:
        # for data_set in self.data:
        #     data_set.setdefault('description', '')
        pass

    def create_topics_by_id_dict(self) -> None:
        """
        Creates a dictionary mapping topic IDs to their data.
        """
        for topic in self.data:
            topic_id = topic.get('id')
            if topic_id is not None:
                self.topics_by_id[int(topic_id)] = topic

    def save_to_file(self) -> None:
        """
        Saves the topics to the JSON file.
        """
        with open(self.json_path, 'w', encoding='utf-8') as file:
            json.dump(self.data, file, indent=4)

        logging.info(f'Saved {len(self.data)} topics to {self.json_path}.')

    def create_new_topic(self, topic: dict[str, str | int | float | bool]) \
    -> None:
        """
        Add a new topic to `data` and `topics_by_id` and save it to JSON file.

        Parameters
        ----------
        topic : dict[str, str | int | float | bool]
            The topic data to be added.
        """
        self.data.append(topic)
        self.topics_by_id[int(topic['id'])] = topic
        self.save_to_file()

    def update_topic(
        self,
        topic_id: int,
        updated_topic: dict[str, str | int | float | bool]
    ) -> None:
        """
        Updates a topic in `data` and `topics_by_id` and saves the changes
        to the JSON file.

        Parameters
        ----------
        topic_id : int
            The ID of the topic to be updated.
        updated_topic : dict[str, str | int | float | bool]
            The updated topic data.
        """
        old_topic_data = self.topics_by_id.get(topic_id)
        if old_topic_data is None:
            logging.warning(f'Topic with ID {topic_id} not found.')
            return

        # Remove the old topic data from `data` and append the updated topic
        self.data.remove(old_topic_data)
        self.data.append(updated_topic)

        # Update the `topics_by_id` dictionary and save to file
        self.topics_by_id[topic_id].update(updated_topic)
        self.save_to_file()

    def delete_topic(self, topic_id: int) -> None:
        """
        Deletes a topic from `data` and `topics_by_id` and saves the changes
        to the JSON file.

        Parameters
        ----------
        topic_id : int
            The ID of the topic to be deleted.
        """
        topic = self.topics_by_id.pop(topic_id, None)
        if topic:
            self.data.remove(topic)
            self.save_to_file()