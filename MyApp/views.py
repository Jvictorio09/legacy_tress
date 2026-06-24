from django.views.generic import TemplateView


class IndexView(TemplateView):
    template_name = 'index.html'


class PoliciesView(TemplateView):
    template_name = 'policies.html'


class OrchestraView(TemplateView):
    template_name = 'orchestra.html'


class PlanView(TemplateView):
    template_name = 'plan.html'


class TryOnView(TemplateView):
    template_name = 'try_on.html'
