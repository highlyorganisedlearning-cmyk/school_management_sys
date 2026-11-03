from django.urls import path
from django.http import HttpResponse
from django.template.response import TemplateResponse
from. import views


def finance_index(request):
    context = {
        'app_list': [
            {
                'name': 'Finance Reports',
                'models': [
                    {'name': 'Download Cashbook', 'admin_url': '/finance/cashbook/'},
                    {'name': 'Download Statements', 'admin_url': '/admin/students/student/'},
                    {'name': 'Download Invoices', 'admin_url': '/admin/students/invoice/'},
                ]
            }
        ]
    }
    return TemplateResponse(request, 'admin/finance_index.html', context)

urlpatterns = [
    path('', finance_index, name='finance_index'),
    path('cashbook/', views.download_cashbook, name='download_cashbook'),
]


def cashflow_statement(request):
    return HttpResponse("Cash Flow Statement - Building this next Boss")

def income_statement(request):
    return HttpResponse("Income Statement - Building this next Boss")

urlpatterns = [
    path('', finance_index, name='finance_index'),
    path('cashbook/', views.download_cashbook, name='download_cashbook'),
    path('cashflow/', cashflow_statement, name='cashflow_statement'), # ADD
    path('incomestatement/', income_statement, name='income_statement'), # ADD
]
