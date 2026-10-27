"""Comprueba identidad de acontecimientos con titulares ficticios, sin escribir datos."""

from types import SimpleNamespace

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from news.llm_grouping import GroupingError, group_articles


class Command(BaseCommand):
    help = "Evalúa un proveedor con tres pares de titulares ficticios; no lee ni escribe noticias."

    def add_arguments(self, parser):
        parser.add_argument("--provider", choices=["gemini", "groq"], default="gemini")

    def handle(self, *args, **options):
        titles = [
            "La editorial ficticia Faro publica hoy su estudio sobre IA en los libros más vendidos",
            "Fictional publisher Faro releases its study on AI in bestselling books today",
            "El banco ficticio Delta aprueba hoy un dividendo de 20 millones para sus accionistas",
            "Delta, banco ficticio, acuerda hoy repartir 20 millones a sus accionistas como dividendo",
            "La empresa ficticia Nimbo presenta hoy su visor doméstico CasaVisión con control por voz",
            "Nimbo, compañía ficticia, lanza hoy CasaVisión, su visor para el hogar controlado por voz",
        ]
        source = SimpleNamespace(name="Medio ficticio de comprobación")
        articles = [SimpleNamespace(
            pk=index, title=title, feed=SimpleNamespace(source=source),
            published_at=timezone.now(), language="en" if index == 2 else "es",
        ) for index, title in enumerate(titles, start=1)]
        try:
            groups = group_articles(articles, [], provider=options["provider"])
        except GroupingError as error:
            raise CommandError(str(error)) from error
        actual = {frozenset(group["article_ids"]) for group in groups}
        expected = {frozenset({1, 2}), frozenset({3, 4}), frozenset({5, 6})}
        if actual != expected:
            raise CommandError("La prueba sintética no separó los tres hechos conservando sus pares; no se deben aplicar uniones.")
        self.stdout.write(f"Comprobación sintética aprobada: tres hechos separados, sus pares unidos y traducción conservada. Proveedor solicitado: {options['provider']}. Modelo: {getattr(groups, 'model', 'no disponible')}.")
