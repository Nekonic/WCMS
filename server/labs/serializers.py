from rest_framework import serializers

from labs.models import PC, RegistrationPin, Room

MAX_SIDE = 20


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ["id", "name", "rows", "cols", "aisle_after", "sort_order"]

    def validate(self, attrs: dict) -> dict:
        current = self.instance
        rows = attrs.get("rows", current.rows if current else 5)
        cols = attrs.get("cols", current.cols if current else 8)
        aisle = attrs.get("aisle_after", current.aisle_after if current else None)
        errors = {}
        if not 1 <= rows <= MAX_SIDE:
            errors["rows"] = [f"1~{MAX_SIDE} 사이로 입력하세요."]
        if not 1 <= cols <= MAX_SIDE:
            errors["cols"] = [f"1~{MAX_SIDE} 사이로 입력하세요."]
        if aisle is not None and not 1 <= aisle < cols:
            errors["aisle_after"] = ["1 이상, 열 수보다 작게 입력하세요."]
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class SeatSerializer(serializers.Serializer):
    row = serializers.IntegerField(min_value=0)
    col = serializers.IntegerField(min_value=0)
    pc = serializers.PrimaryKeyRelatedField(queryset=PC.objects.all())


class SeatsSerializer(serializers.Serializer):
    seats = SeatSerializer(many=True)

    def validate_seats(self, seats: list[dict]) -> list[dict]:
        room: Room = self.context["room"]
        positions: set[tuple[int, int]] = set()
        pcs: set[int] = set()
        for entry in seats:
            position = (entry["row"], entry["col"])
            if entry["row"] >= room.rows or entry["col"] >= room.cols:
                raise serializers.ValidationError("실습실 크기를 벗어난 자리가 있습니다.")
            if position in positions:
                raise serializers.ValidationError("같은 자리에 두 PC를 배치할 수 없습니다.")
            if entry["pc"].id in pcs:
                raise serializers.ValidationError("같은 PC를 두 자리에 배치할 수 없습니다.")
            positions.add(position)
            pcs.add(entry["pc"].id)
        return seats


class PCSerializer(serializers.ModelSerializer):
    label = serializers.CharField(read_only=True)

    class Meta:
        model = PC
        fields = ["id", "hostname", "label", "room", "row", "col", "client_version", "specs", "registered_at"]


class PinSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistrationPin
        fields = ["id", "pin", "multi_use", "expires_at", "used_count", "created_at"]


class PinCreateSerializer(serializers.Serializer):
    multi_use = serializers.BooleanField(default=False)
    minutes = serializers.ChoiceField(choices=[10, 60, 180])
