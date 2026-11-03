from django import forms
from kids.models import CourseWorkScore, CourseWorkMarkSheet

class CourseWorkMarkSheetForm(forms.ModelForm):
    class Meta:
        model = CourseWorkMarkSheet
        fields = [
            'out_ex1','out_ex2','out_ex3','out_ex4','out_ex5','out_ex6','out_ex7',
            'out_test1','out_test2',
            'date_ex1','date_ex2','date_ex3','date_ex4','date_ex5','date_ex6','date_ex7',
            'date_test1','date_test2'
        ]
        widgets = {
            'date_ex1': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
            'date_ex2': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
            'date_ex3': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
            'date_ex4': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
            'date_ex5': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
            'date_ex6': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
            'date_ex7': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
            'date_test1': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
            'date_test2': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if 'out_' in field:
                self.fields[field].widget.attrs.update({'class': 'form-control form-control-sm'})

class CourseWorkScoreForm(forms.ModelForm):
    class Meta:
        model = CourseWorkScore
        fields = ['student', 'ex1','ex2','ex3','ex4','ex5','ex6','ex7','test1','test2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['student'].widget = forms.HiddenInput()
        for field in ['ex1','ex2','ex3','ex4','ex5','ex6','ex7','test1','test2']:
            self.fields[field].widget.attrs.update({
                'autocomplete': 'off',
                'class': 'form-control form-control-sm text-center',
                'maxlength': '3'
            })

    def clean(self):
        cleaned_data = super().clean()
        for field in ['ex1','ex2','ex3','ex4','ex5','ex6','ex7','test1','test2']:
            val = cleaned_data.get(field)
            if val:
                val = str(val).upper().strip()
                if val not in ['A','S'] and not val.replace('.','',1).isdigit():
                    self.add_error(field, 'Enter Number, A, or S only')
        return cleaned_data
