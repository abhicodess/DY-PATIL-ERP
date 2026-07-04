from flask import render_template, request, redirect, url_for, flash, session
from blueprints.results import results_bp
from blueprints.auth.decorators import login_required, admin_required
from services.results_service import ResultsService

results_service = ResultsService()

@results_bp.route("/")
@login_required(["admin", "faculty", "student"])
def index():
    if session.get("role") == "admin":
        return redirect("/admin_results")
    return render_template("results/results_dashboard.html")

@results_bp.route("/add", methods=["GET", "POST"])
@admin_required
def add():
    if request.method == "POST":
        # results_service.add_marks(request.form.to_dict())
        flash("Marks added successfully", "success")
        return redirect(url_for('results.index'))
    return render_template("results/add_marks.html")
