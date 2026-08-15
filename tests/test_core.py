import tempfile
import unittest
from pathlib import Path

from phagetriage.fasta import infer_topology, read_fasta
from phagetriage.cli import parser
from phagetriage.models import Finding, SampleResult
from phagetriage.parsers import parse_pharokka, parse_rafah, parse_replidec, parse_viralcomplete
from phagetriage.report import _features, write_reports
from phagetriage.scoring import assign_verdict


class CoreTests(unittest.TestCase):
    def test_beginner_demo_command_is_available(self):
        args = parser().parse_args(["demo", "--threads", "2"])
        self.assertEqual(args.command, "demo")
        self.assertEqual(args.threads, 2)

    def test_reads_and_detects_terminal_overlap(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "x.fa"
            overlap = "ACGTCAGTACGATCGTACGA"
            path.write_text(">p1\n" + overlap + "TTGGAACCTT" + overlap + "\n")
            record = read_fasta(path)[0]
            infer_topology(record, "auto", 20, 500)
            self.assertEqual(record.topology, "circular_candidate")
            self.assertEqual(record.terminal_overlap, 20)

    def test_hard_exclusion_wins(self):
        result = SampleResult("p", 100, 50.0, "linear", "user", 0)
        result.replication_cycle = Finding("lytic", "ok")
        result.amr = Finding([{"gene": "x"}], "ok")
        result.virulence = Finding([], "ok")
        result.completeness = Finding("complete", "ok")
        result.host = Finding("E_coli", "ok")
        result.taxonomy = Finding("Caudoviricetes", "ok")
        assign_verdict(result)
        self.assertEqual(result.verdict, "EXCLUDE")

    def test_missing_evidence_is_review(self):
        result = SampleResult("p", 100, 50.0, "linear", "user", 0)
        assign_verdict(result)
        self.assertEqual(result.verdict, "REVIEW")

    def test_pharokka_virulence_uses_vfdb_data_rows(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "pharokka" / "p"
            root.mkdir(parents=True)
            vfdb = root / "p_top_hits_vfdb.tsv"
            vfdb.write_text("query\ttarget\tevalue\n")
            result = SampleResult("p", 100, 50.0, "linear", "user", 0)
            parse_pharokka(root.parent, {"p": result}, "complete")
            self.assertEqual(result.virulence.value, [])
            vfdb.write_text("query\ttarget\tevalue\ncds1\tVF0001\t1e-20\n")
            parse_pharokka(root.parent, {"p": result}, "complete")
            self.assertEqual(len(result.virulence.value), 1)

    def test_failed_pharokka_run_cannot_become_no_hit_pass(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "pharokka" / "p"
            root.mkdir(parents=True)
            (root / ".phagetriage_status").write_text("failed:1\n")
            (root / "p_top_hits_vfdb.tsv").write_text("query\ttarget\tevalue\n")
            result = SampleResult("p", 100, 50.0, "linear", "user", 0)
            parse_pharokka(root.parent, {"p": result}, "complete")
            self.assertEqual(result.virulence.value, [])
            self.assertEqual(result.virulence.status, "failed:1")

    def test_replidec_final_label_takes_precedence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            root.joinpath("prediction_summary.tsv").write_text(
                "sample_name\tpfam_label\tbc_label\tfinal_label\n"
                "p\tVirulent\tTemperate\tChronic\n"
            )
            result = SampleResult("p", 100, 50.0, "linear", "user", 0)
            parse_replidec(root, {"p": result}, "complete")
            self.assertEqual(result.replication_cycle.value, "chronic")

    def test_headerless_viralcomplete_result(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            root.joinpath("all_contigs_result_table.csv").write_text(
                'p,14935,100.0%,Full-length,p,14935,"phage, complete genome"\n'
            )
            result = SampleResult("p", 14935, 40.0, "linear", "user", 0)
            parse_viralcomplete(root, {"p": result}, "complete")
            self.assertEqual(result.completeness.value, "complete")
            self.assertEqual(result.completeness.status, "ok")

    def test_headerless_multiphage_viralcomplete_result(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            root.joinpath("all_contigs_result_table.csv").write_text(
                "p1,100,98.9%,Full-length,r1,101,reference one\n"
                "p2,200,100.0%,Full-length,r2,200,reference two\n"
            )
            results = {
                name: SampleResult(name, size, 40.0, "linear", "user", 0)
                for name, size in (("p1", 100), ("p2", 200))
            }
            parse_viralcomplete(root, results, "complete")
            self.assertEqual(results["p1"].completeness.value, "complete")
            self.assertEqual(results["p2"].completeness.value, "complete")

    def test_escaped_tab_gff_is_mapped(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            root.joinpath("p.gff").write_text(
                "##gff-version 3\n"
                "p\\tpharokka\\tCDS\\t1\\t30\\t.\\t+\\t0\\t"
                "ID=cds1;locus_tag=cds1;function=head;product=major capsid protein\\t\n"
            )
            features = _features(root)
            self.assertEqual(len(features), 1)
            self.assertEqual(features[0]["product"], "major capsid protein")

    def test_rafah_prediction_is_parsed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            root.joinpath("RaFAH_Seq_Info_Prediction.tsv").write_text(
                "source file\tPredicted_Host\tPredicted_Host_Score\n"
                "p.fasta\tEscherichia\t0.93\n"
            )
            result = SampleResult("p", 100, 50.0, "linear", "user", 0)
            parse_rafah(root, {"p": result}, "complete")
            self.assertIn("Escherichia", result.host.value)
            self.assertEqual(result.host.status, "ok")

    def test_snakemake_workflow_has_requested_lean_stack(self):
        snakefile = Path(__file__).parents[1] / "src/phagetriage/workflow/Snakefile"
        text = snakefile.read_text()
        for rule in ("rule pharokka", "rule replidec", "rule viralcomplete", "rule taxmyphage", "rule rafah"):
            self.assertIn(rule, text)
        for removed in ("iphop", "genomad", "bacphlip"):
            self.assertNotIn(removed, text.lower())

    def test_one_command_installer_contains_all_tools(self):
        root = Path(__file__).parents[1]
        installer = (root / "install_all.sh").read_text()
        for tool in ("pharokka", "replidec", "taxmyphage", "viralComplete", "RaFAH"):
            self.assertIn(tool, installer)
        for wrapper in ("phagetriage", "pharokka", "Replidec", "taxmyphage", "viralcomplete", "RaFAH.py"):
            self.assertTrue((root / "installer/wrappers" / wrapper).exists())
        self.assertTrue((root / "phagetriage.sh").exists())

    def test_clean_report_contains_map_and_assessment_matrix(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            gff_dir = out / "tools/pharokka/p"
            gff_dir.mkdir(parents=True)
            gff_dir.joinpath("p.gff").write_text(
                "##gff-version 3\n"
                "p\tpharokka\tCDS\t1\t30\t.\t+\t0\tID=cds1;product=major capsid protein\n"
            )
            record = read_fasta(self._fasta(out, ">p circular\n" + "ACGT" * 25 + "\n"))[0]
            infer_topology(record, "auto", 20, 500)
            result = SampleResult("p", record.length, record.gc_percent, record.topology, record.topology_evidence, 0)
            result.replication_cycle = Finding("lytic", "ok")
            result.amr = Finding([], "ok")
            result.virulence = Finding([], "ok")
            result.completeness = Finding("complete", "ok")
            result.host = Finding("host_A", "ok")
            result.taxonomy = Finding("Caudoviricetes", "ok")
            result.annotation = Finding("available", "ok")
            assign_verdict(result)
            write_reports(out, [record], {"p": result}, {"workflow": "test"})
            page = (out / "report/index.html").read_text()
            self.assertIn("Executive summary", page)
            self.assertIn("Assessment checklist", page)
            self.assertIn("Analysis run status", page)
            self.assertIn("Circular annotated genome map", page)
            self.assertIn("Pharokka VFDB", page)
            self.assertIn("<h1>PhageTriage Report</h1>", page)
            self.assertIn("Selected CDS annotations", page)

    @staticmethod
    def _fasta(root: Path, text: str) -> Path:
        path = root / "input.fasta"
        path.write_text(text)
        return path


if __name__ == "__main__":
    unittest.main()
