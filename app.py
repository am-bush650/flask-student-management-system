from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask import render_template, request, redirect, url_for, flash, jsonify, send_file
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import io
import csv
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas