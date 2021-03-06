from nameko.web.handlers import http
from nameko.rpc import RpcProxy, rpc
from nameko_mongodb import MongoDatabase
from werkzeug.wrappers import Request, Response
from bson.objectid import ObjectId
from nameko.events import EventDispatcher
import json


class EventsDAS:
    # Vars

    name = "event_das"
    db = MongoDatabase()
    eta = RpcProxy("event_theme_analyzer")
    logger_rpc = RpcProxy('logger')
    dispatch = EventDispatcher()

    # Logic

    def _check_event_presence(self, event):
        """Checks whether event is present in collection of
        events

        Args:
            event (dict): plain event dictionary

        Returns:
            (bool, event): 1st argument tells whether event is
            present in the collection, second is event from the
            collection
        """
        meta = event["meta"]

        filter = {
            "$or": [
                {"meta.{}".format(key): meta[key] for key in meta}
            ]
        }

        in_collection_event = self.db["events"].find_one(filter)

        return in_collection_event is not None, in_collection_event

    def _process_events_save(self, events: dict) -> list:
        """Saves a collection of events analyzing them on updates
        and theme tags. If event is already present in the system
        than we just try to update it, if not, then we send it
        to be analyzed on themes to acquire theme tags

        Args:
            events (dict): events to be saved or analyzed

        Returns:
            list: stringed ObjectIds for saved events
        """
        self.logger_rpc.log(self.name, self._process_events_save.__name__, events, "Info", "Starting saving processing")

        collection = self.db["events"]

        new_events = []

        is_new_info = False  # True in case of info of existing events being updated

        for event in events:
            is_present, saved_event = self._check_event_presence(event)

            print("{} is present".format(str(
                saved_event["_id"])) if is_present else "{} is not present".format(event["title"]))

            if is_present:
                # TODO: think if this update scheme is enough
                # we want to check most vulnerable for update information:
                # - location
                # - date
                # - online format
                # we compose update request

                update = dict()

                if event["location"] != saved_event["location"]:
                    update["location"] = event["location"]

                if event["startDate"] != saved_event["startDate"]:
                    update["startDate"] = event["startDate"]

                if event["endDate"] != saved_event["endDate"]:
                    update["endDate"] = event["endDate"]

                print("Update: {}".format(update))

                if len(update) > 0:
                    collection.update(
                        {"_id": saved_event["_id"]},
                        {"$set": update})
                    is_new_info = True
            else:
                new_events.append(event)

        self.logger_rpc.log(self.name, self._process_events_save.__name__, events, "Info", "Analyzing new events")
        try:
            new_events = self.eta.analyze_events(new_events)
        except:
            self.logger_rpc.log(self.name, self._process_events_save.__name__, events, "Error", "Can't analyze new events")

        if len(new_events) > 0:
            collection.insert_many(new_events)
            self.dispatch("new_events", "")
        elif is_new_info:
            self.dispatch("new_events", "")
        self.logger_rpc.log(self.name, self._process_events_save.__name__, events, "Info", "New events saved")

        ids = self._find_expired()
        if len(ids) > 0:
            self.dispatch("expired_events", ids)

            for id in ids:
                self._delete_event_by_id(id)
        self.logger_rpc.log(self.name, self._process_events_save.__name__, events, "Info", "Old events removed")
        

    def _get_event_by_id(self, id):
        return self.db["events"].find_one({"_id": ObjectId(id)})

    def _date_key(self, date):
        """Making correct format for date

        Args:
            date (str): date in format "dd.mm.yyyy"

        Rerurns:
            date (datetime.date): date for comparing"""
        import datetime

        date = date.split('.')
        date = [int(elem) for elem in date]
        return datetime.date(date[2], date[1], date[0])

    def _find_expired(self):
        """Checks db for expired events and returns list of ids"""
        import datetime

        event_ids = list()

        cursor = self.db["events"].find(
            {}, {"_id": 1, "startDate": 1, "endDate": 1})
        for row in cursor:
            if row["endDate"] is not None and datetime.datetime.now().date() > self._date_key(row["endDate"]) or row["endDate"] is None and datetime.datetime.now().date() > self._date_key(row["startDate"]):
                event_ids.append(str(row["_id"]))
        return event_ids

    def _delete_event_by_id(self, id):
        self.db["events"].delete_one({"_id": ObjectId(id)})

    # API

    @rpc
    def save_events(self, events):
        """RPC handler for _save_events() method

        Args:
            events (list): of event dicts
        """
        self._process_events_save(events)

        return

    @rpc
    def get_event_by_id(self, id):
        """RPC handler for _get_event_by_id() method

        Args:
            id (str): event id of string type (ObjectId)

        Returns:
            dict: event as dictionary object
        """
        event = self._get_event_by_id(id)
        event["_id"] = str(event["_id"])
        return event

    @rpc
    def get_events_by_date(self):
        """Getting all events sorted by date

        Returns:
            events (list): sorted by date list of events"""
        # Getting all actual events
        cursor = self.db['events'].find()
        events = list()
        for row in cursor:
            row["_id"] = str(row["_id"])
            events.append(row)

        # Sorting by date
        self.logger_rpc.log(self.name, self.get_events_by_date.__name__, None, "Info", "Getting all events by date")
        return sorted(events, key=lambda event: self._date_key(event['startDate']))

    @rpc
    def get_tags_by_id(self, event_id):
        """Getting event tags by its id

        Args:
            event_id (str): id for event

        Returns:
            tags (list): list of event tags"""
        self.logger_rpc.log(self.name, self.get_tags_by_id.__name__, event_id, "Info", "Getting tags by event_id")

        return self._get_event_by_id(event_id)['tags']

    @rpc
    def get_event_tags(self):
        """Getting event_id with tags for this event

        Returns:
            events (dict): events in format 
            {'event_id_1': ['tag_1',...,'tag_n'], ..., 
            'event_id_m':['tag_1',...,'tag_k']}"""

        events = dict()
        cursor = self.db['events'].find()
        for event in cursor:
            events[str(event["_id"])] = event["tags"]
        self.logger_rpc.log(self.name, self.get_event_tags.__name__, None, "Info", "Getting all event ids with tags")
        return events

    @http('GET', '/events/<string:id>/tags')
    def get_tags_by_id_handler(self, request, id):
        """Handler for get_tags_by_id() method

        Args:
            id (str): id (str): stringified ObjectId

        Returns: http response with tags"""

        tags = self.get_tags_by_id(id)
        return 200, {"Content-Type": "application/json"}, json.dumps(tags, ensure_ascii=False)

    @http('GET', '/tags')
    def get_event_tags_handler(self, request):
        """Handler for get_event_tags() method

        Returns: http response with dict of ids and tags"""

        event_tags = self.get_event_tags()
        return 200, {"Content-Type": "application/json"}, json.dumps(event_tags, ensure_ascii=False)

    @http('GET', '/allevents')
    def get_events_by_date_handler(self, request):
        """Handler for get_events_by_date() method

        Response:
            http response with events in body"""
        events = self.get_events_by_date()
        return 200, {"Content-Type": "application/json"}, json.dumps(events, ensure_ascii=False)

    @http("POST", "/events")
    def process_events_handler(self, request: Request):
        """Handler for _save_events() method

        Args:
            request (Request): http request with events in body

        Returns:
            (Response): Status Code: 201
        """
        content = request.get_data(as_text=True)

        events = json.loads(content)

        self._process_events_save(events)

        return Response(status=201)

    @http("GET", "/events/<string:id>")
    def get_event_by_id_handler(self, request: Request, id: str):
        """Get exactly one or zero events by id 

        Args:
            request (Request): HTTP request
            id (str): stringified ObjectId

        Returns:
            Response: Status Code: 200; Payload: event
        """

        event = self._get_event_by_id(id) or {}

        event["_id"] = str(event["_id"])
        return 200, {"Content-Type": "application/json"}, json.dumps(event, ensure_ascii=False)
