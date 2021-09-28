from enum import Enum
import datetime
import base64


class ImagebusTopic(Enum):

    SOURCE_FRAME = 1
    IMAGEAI_FRAME = 2
    REDACTION_FRAME = 3

    def __str__(self):
        return self.name


class FrameDetails:
    def __init__(
        self,
        name,
        topic,
        frameRate=1,
        url=None,
        parent=None,
        details=None,
        speed=None,
        average=None,
    ):
        print(
            "Create FrameDetails: name=%s frameRate=%d url=%s, topic=%s"
            % (name, frameRate, url, topic)
        )
        if name is None:
            self.name = url
        else:
            self.name = name

        self.frameRate = frameRate
        self.url = url
        self.dateTime = datetime.datetime.now()
        self.frameReference = 0
        self.topic = topic
        self.image = None
        self.parent = parent
        self.details = details
        self.speed = speed
        self.average = average

    @staticmethod
    def datetimefilter(value, format="%Y/%m/%d %H:%M:%S.%f"):
        """convert a datetime to a different format."""
        format = "%H:%M:%S.%f"
        return value.strftime(format)

    def __str__(self):
        return "FrameDetails( \n Name={} \n url={} \n frameRate={} \n frameReference={} \n topic={} \n datetime={} \n parent={} \n details={}\n)".format(
            self.name,
            self.url,
            self.frameRate,
            self.frameReference,
            self.topic,
            self.dateTime,
            self.parent,
            self.details,
        )

    def setFrame(self, frameReference, image):
        self.frameReference = frameReference
        self.image = image
        self.dateTime = datetime.datetime.now()

    def setChildFrame(self, frameReference, image, details, parent, speed, average):
        self.setFrame(frameReference, image)
        self.details = details
        self.parent = parent
        self.speed = speed
        self.average = average

    def createResponse(self):

        encoded_image = "data:image/jpg;base64," + base64.b64encode(self.image).decode(
            "utf8"
        )

        return {
            "name": self.name,
            "image": encoded_image,
            "time": self.datetimefilter(self.dateTime),
            "frame_reference": self.frameReference,
            "details": self.details,
            "performance": {"speed": self.speed, "average": self.average},
        }


if __name__ == "__main__":
    print("Welcome to imagebusutil module")
