from django import forms
from .models import Student, FeeStructure


grade = forms.ModelChoiceField(
    queryset=FeeStructure.objects.all().order_by('grade'),
    to_field_name='grade',
    empty_label="Select Grade"
)


class StudentForm(forms.ModelForm):
    grade = forms.ModelChoiceField(
        queryset=FeeStructure.objects.all(),
        to_field_name='grade',
        empty_label="--- Select Grade ---"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['grade'].label_from_instance = lambda obj: obj.grade

    class Meta:
        model = Student
        fields = ['adm_no', 'first_name', 'last_name', 'grade']

