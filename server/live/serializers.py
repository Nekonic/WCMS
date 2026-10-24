from rest_framework import serializers


class ForegroundSerializer(serializers.Serializer):
    process = serializers.CharField(allow_blank=True)
    title = serializers.CharField(allow_blank=True)


class LivePCSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    hostname = serializers.CharField()
    label = serializers.CharField()
    room = serializers.IntegerField(allow_null=True)
    row = serializers.IntegerField(allow_null=True)
    col = serializers.IntegerField(allow_null=True)
    version = serializers.CharField(allow_blank=True)
    online = serializers.BooleanField()
    session = serializers.ChoiceField(choices=["active", "locked", "none"])
    user = serializers.CharField(allow_blank=True)
    foreground = ForegroundSerializer(allow_null=True)
    cpu = serializers.FloatField(allow_null=True)
    mem_used = serializers.FloatField(allow_null=True)
    mem_total = serializers.FloatField(allow_null=True)
    disk_used = serializers.FloatField(allow_null=True)
    disk_total = serializers.FloatField(allow_null=True)


class PublicSeatSerializer(serializers.Serializer):
    row = serializers.IntegerField()
    col = serializers.IntegerField()
    label = serializers.CharField()
    online = serializers.BooleanField()


class PublicRoomSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    rows = serializers.IntegerField()
    cols = serializers.IntegerField()
    aisle_after = serializers.IntegerField(allow_null=True)


class PublicRoomDetailSerializer(serializers.Serializer):
    room = PublicRoomSerializer()
    seats = PublicSeatSerializer(many=True)
