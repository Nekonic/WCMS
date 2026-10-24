from django import forms

from labs.models import Room

MAX_SIDE = 20


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ["name", "rows", "cols", "aisle_after", "sort_order"]
        labels = {
            "name": "이름",
            "rows": "줄 수",
            "cols": "열 수",
            "aisle_after": "통로 위치 (N번째 열 뒤, 비우면 없음)",
            "sort_order": "정렬 순서",
        }

    def clean(self) -> dict:
        data = super().clean()
        rows, cols, aisle = data.get("rows"), data.get("cols"), data.get("aisle_after")
        if rows is not None and not 1 <= rows <= MAX_SIDE:
            self.add_error("rows", f"1~{MAX_SIDE} 사이로 입력하세요.")
        if cols is not None and not 1 <= cols <= MAX_SIDE:
            self.add_error("cols", f"1~{MAX_SIDE} 사이로 입력하세요.")
        if aisle is not None and cols is not None and not 1 <= aisle < cols:
            self.add_error("aisle_after", "1 이상, 열 수보다 작게 입력하세요.")
        return data


class PinForm(forms.Form):
    multi_use = forms.BooleanField(required=False, label="여러 대에 사용")
    minutes = forms.TypedChoiceField(
        choices=[(10, "10분"), (60, "1시간"), (180, "3시간")],
        coerce=int,
        initial=10,
        label="유효 시간",
    )
