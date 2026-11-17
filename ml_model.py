"""
Machine Learning Module for GitHub MCDM Analysis
=================================================

This module implements ML models to predict TOPSIS scores based on GitHub metrics.
Using Multi-Criteria Decision Making Methods"


Approach: MCDM + ML Hybrid
- Uses TOPSIS scores (calculated via MCDM) as target variable
- Trains ML models to predict success scores from raw GitHub metrics
- Validates MCDM results through ML feature importance analysis

References:
- Breiman, L. (2001). Random Forests. Machine Learning, 45(1), 5-32.
- Chen, T., & Guestrin, C. (2016). XGBoost: A Scalable Tree Boosting System.
- Pedregosa et al. (2011). Scikit-learn: Machine Learning in Python.
"""

import os
import numpy as np
import pandas as pd
import mysql.connector
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Scikit-learn imports
from sklearn.model_selection import train_test_split, cross_val_score, KFold
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.inspection import permutation_importance

# XGBoost
try:
    from xgboost import XGBRegressor
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("Warning: XGBoost not installed. Run: pip install xgboost")

# Visualization
import matplotlib.pyplot as plt
import seaborn as sns

# Set style
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 11
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12


# =============================================================================
# DATABASE CONNECTION & DATA LOADING
# =============================================================================

def get_db_connection():
    """
    Establish MySQL database connection.
    
    Returns:
        mysql.connector.connection: Active database connection
    """
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=os.environ.get("MYSQL_PASSWORD", ""),
        database="github_analysis"
    )


def load_data():
    """
    Load GitHub repository data from MySQL database.
    
    Returns:
        pd.DataFrame: Repository data with all metrics
    """
    conn = get_db_connection()
    
    query = """
    SELECT 
        r.id,
        r.full_name,
        r.stars,
        r.forks,
        r.open_issues,
        r.watchers,
        r.created_at,
        r.updated_at,
        r.language,
        COALESCE(c.contributor_count, 0) as contributors,
        COALESCE(ca.total_commits, 0) as commits
    FROM repositories r
    LEFT JOIN (
        SELECT repo_id, COUNT(*) as contributor_count 
        FROM contributors 
        GROUP BY repo_id
    ) c ON r.id = c.repo_id
    LEFT JOIN (
        SELECT repo_id, SUM(total_commits) as total_commits 
        FROM commit_activity 
        GROUP BY repo_id
    ) ca ON r.id = ca.repo_id
    WHERE r.stars > 0
    ORDER BY r.stars DESC
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    # Calculate derived features
    now = datetime.now()
    
    # Project age (days)
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['project_age_days'] = (now - df['created_at']).dt.days
    
    # Days since last update (recency)
    df['updated_at'] = pd.to_datetime(df['updated_at'])
    df['days_since_update'] = (now - df['updated_at']).dt.days
    
    # Handle missing values
    df['contributors'] = df['contributors'].fillna(0).astype(int)
    df['commits'] = df['commits'].fillna(0).astype(int)
    
    print(f"Loaded {len(df)} repositories from database")
    
    return df


# =============================================================================
# TOPSIS CALCULATION (for target variable)
# =============================================================================

def calculate_topsis_scores(df, weights=None):
    """
    Calculate TOPSIS scores for all repositories.
    
    This function implements the TOPSIS method to generate target variable
    for ML model training.
    
    Parameters:
        df (pd.DataFrame): Repository data
        weights (np.array): Criteria weights (default: AHP weights)
    
    Returns:
        np.array: TOPSIS scores (0-1 range)
    
    Reference:
        Hwang, C.L., & Yoon, K. (1981). Multiple Attribute Decision Making.
    """
    # Define criteria columns
    criteria_cols = ['stars', 'forks', 'contributors', 'commits', 
                     'days_since_update', 'watchers', 'project_age_days']
    
    # Extract decision matrix
    matrix = df[criteria_cols].values.astype(float)
    
    # Handle zero/missing values
    matrix = np.where(matrix == 0, 0.001, matrix)
    
    # Default weights (from AHP analysis)
    if weights is None:
        weights = np.array([0.3047, 0.1858, 0.1078, 0.1078, 0.0652, 0.1858, 0.0427])
    
    # Impact directions: 1=benefit (higher is better), -1=cost (lower is better)
    impacts = np.array([1, 1, 1, 1, -1, 1, 1])
    
    # Step 1: Normalize the decision matrix (vector normalization)
    norm_matrix = matrix / np.sqrt((matrix ** 2).sum(axis=0))
    
    # Step 2: Weighted normalized matrix
    weighted_matrix = norm_matrix * weights
    
    # Step 3: Determine ideal and anti-ideal solutions
    ideal = np.zeros(len(criteria_cols))
    anti_ideal = np.zeros(len(criteria_cols))
    
    for j in range(len(criteria_cols)):
        if impacts[j] == 1:  # Benefit criterion
            ideal[j] = weighted_matrix[:, j].max()
            anti_ideal[j] = weighted_matrix[:, j].min()
        else:  # Cost criterion
            ideal[j] = weighted_matrix[:, j].min()
            anti_ideal[j] = weighted_matrix[:, j].max()
    
    # Step 4: Calculate distances
    dist_ideal = np.sqrt(((weighted_matrix - ideal) ** 2).sum(axis=1))
    dist_anti_ideal = np.sqrt(((weighted_matrix - anti_ideal) ** 2).sum(axis=1))
    
    # Step 5: Calculate TOPSIS scores
    scores = dist_anti_ideal / (dist_ideal + dist_anti_ideal + 1e-10)
    
    return scores


# =============================================================================
# FEATURE ENGINEERING
# =============================================================================

def prepare_features(df):
    """
    Prepare feature matrix for ML models.
    
    Creates both raw and engineered features for better model performance.
    
    Parameters:
        df (pd.DataFrame): Repository data
    
    Returns:
        tuple: (X, feature_names) - Feature matrix and column names
    """
    # Primary features (raw metrics)
    primary_features = ['stars', 'forks', 'contributors', 'commits', 
                        'watchers', 'project_age_days', 'days_since_update']
    
    X = df[primary_features].copy()
    
    # Engineered features (ratios and interactions)
    # These capture relationships between metrics
    
    # Engagement ratio: forks per star
    X['forks_per_star'] = df['forks'] / (df['stars'] + 1)
    
    # Community ratio: contributors per fork
    X['contributors_per_fork'] = df['contributors'] / (df['forks'] + 1)
    
    # Activity ratio: commits per contributor
    X['commits_per_contributor'] = df['commits'] / (df['contributors'] + 1)
    
    # Popularity velocity: stars per day of existence
    X['stars_per_day'] = df['stars'] / (df['project_age_days'] + 1)
    
    # Issue handling: open issues per star (lower is better)
    X['issues_per_star'] = df['open_issues'] / (df['stars'] + 1)
    
    # Watcher engagement: watchers per star
    X['watchers_per_star'] = df['watchers'] / (df['stars'] + 1)
    
    # Activity freshness: commits per day since update
    X['commit_freshness'] = df['commits'] / (df['days_since_update'] + 1)
    
    # Handle infinite and NaN values
    X = X.replace([np.inf, -np.inf], np.nan)
    X = X.fillna(0)
    
    feature_names = X.columns.tolist()
    
    print(f"Created {len(feature_names)} features:")
    print(f"  - Primary features: {len(primary_features)}")
    print(f"  - Engineered features: {len(feature_names) - len(primary_features)}")
    
    return X, feature_names


# =============================================================================
# MODEL TRAINING & EVALUATION
# =============================================================================

class MCDMPredictor:
    """
    Machine Learning predictor for MCDM (TOPSIS) scores.
    
    This class trains multiple ML models to predict TOPSIS scores
    from GitHub metrics, enabling validation of MCDM results and
    identification of key success factors.
    
    Attributes:
        models (dict): Trained ML models
        results (dict): Performance metrics for each model
        feature_names (list): Names of input features
        best_model_name (str): Name of best performing model
    """
    
    def __init__(self):
        self.models = {}
        self.results = {}
        self.feature_names = None
        self.scaler = StandardScaler()
        self.best_model_name = None
        self.X_train = None
        self.X_test = None
        self.y_train = None
        self.y_test = None
        
    def train(self, X, y, feature_names, test_size=0.2, random_state=42):
        """
        Train multiple ML models and evaluate performance.
        
        Parameters:
            X (np.array): Feature matrix
            y (np.array): Target variable (TOPSIS scores)
            feature_names (list): Feature column names
            test_size (float): Proportion of data for testing
            random_state (int): Random seed for reproducibility
        
        Returns:
            dict: Model performance results
        """
        self.feature_names = feature_names
        
        # Split data
        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(self.X_train)
        X_test_scaled = self.scaler.transform(self.X_test)
        
        print("\n" + "="*60)
        print("MODEL TRAINING")
        print("="*60)
        print(f"Training set size: {len(self.X_train)}")
        print(f"Test set size: {len(self.X_test)}")
        print(f"Number of features: {X.shape[1]}")
        
        # Define models
        model_configs = {
            'Linear Regression': LinearRegression(),
            'Ridge Regression': Ridge(alpha=1.0),
            'Random Forest': RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=random_state,
                n_jobs=-1
            ),
            'Gradient Boosting': GradientBoostingRegressor(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=random_state
            )
        }
        
        # Add XGBoost if available
        if XGBOOST_AVAILABLE:
            model_configs['XGBoost'] = XGBRegressor(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=random_state,
                verbosity=0
            )
        
        # Train and evaluate each model
        for name, model in model_configs.items():
            print(f"\nTraining {name}...")
            
            # Use scaled data for linear models, raw for tree-based
            if 'Linear' in name or 'Ridge' in name or 'Lasso' in name:
                model.fit(X_train_scaled, self.y_train)
                y_pred = model.predict(X_test_scaled)
                y_train_pred = model.predict(X_train_scaled)
            else:
                model.fit(self.X_train, self.y_train)
                y_pred = model.predict(self.X_test)
                y_train_pred = model.predict(self.X_train)
            
            # Calculate metrics
            train_r2 = r2_score(self.y_train, y_train_pred)
            test_r2 = r2_score(self.y_test, y_pred)
            mae = mean_absolute_error(self.y_test, y_pred)
            rmse = np.sqrt(mean_squared_error(self.y_test, y_pred))
            
            # Cross-validation
            if 'Linear' in name or 'Ridge' in name:
                cv_scores = cross_val_score(model, X_train_scaled, self.y_train, 
                                           cv=5, scoring='r2')
            else:
                cv_scores = cross_val_score(model, self.X_train, self.y_train, 
                                           cv=5, scoring='r2')
            
            self.models[name] = model
            self.results[name] = {
                'train_r2': train_r2,
                'test_r2': test_r2,
                'mae': mae,
                'rmse': rmse,
                'cv_mean': cv_scores.mean(),
                'cv_std': cv_scores.std(),
                'predictions': y_pred
            }
            
            print(f"  Train R²: {train_r2:.4f}")
            print(f"  Test R²:  {test_r2:.4f}")
            print(f"  MAE:      {mae:.4f}")
            print(f"  RMSE:     {rmse:.4f}")
            print(f"  CV R²:    {cv_scores.mean():.4f} (±{cv_scores.std():.4f})")
        
        # Find best model
        best_r2 = -np.inf
        for name, metrics in self.results.items():
            if metrics['test_r2'] > best_r2:
                best_r2 = metrics['test_r2']
                self.best_model_name = name
        
        print(f"\n{'='*60}")
        print(f"BEST MODEL: {self.best_model_name} (R² = {best_r2:.4f})")
        print(f"{'='*60}")
        
        return self.results
    
    def get_feature_importance(self, model_name=None):
        """
        Extract feature importance from trained model.
        
        Parameters:
            model_name (str): Model to use (default: best model)
        
        Returns:
            pd.DataFrame: Feature importance scores
        """
        if model_name is None:
            model_name = self.best_model_name
        
        model = self.models[model_name]
        
        # Get feature importance based on model type
        if hasattr(model, 'feature_importances_'):
            # Tree-based models
            importance = model.feature_importances_
        elif hasattr(model, 'coef_'):
            # Linear models - use absolute coefficient values
            importance = np.abs(model.coef_)
        else:
            # Use permutation importance as fallback
            perm_importance = permutation_importance(
                model, self.X_test, self.y_test, 
                n_repeats=10, random_state=42
            )
            importance = perm_importance.importances_mean
        
        # Create DataFrame
        importance_df = pd.DataFrame({
            'Feature': self.feature_names,
            'Importance': importance
        })
        importance_df = importance_df.sort_values('Importance', ascending=False)
        importance_df['Importance_Pct'] = (importance_df['Importance'] / 
                                            importance_df['Importance'].sum() * 100)
        
        return importance_df
    
    def print_results_summary(self):
        """Print formatted summary of all model results."""
        print("\n" + "="*80)
        print("MODEL COMPARISON SUMMARY")
        print("="*80)
        print(f"{'Model':<25} {'Train R²':>10} {'Test R²':>10} {'MAE':>10} {'RMSE':>10} {'CV R²':>12}")
        print("-"*80)
        
        for name, metrics in self.results.items():
            marker = " ★" if name == self.best_model_name else ""
            print(f"{name:<25} {metrics['train_r2']:>10.4f} {metrics['test_r2']:>10.4f} "
                  f"{metrics['mae']:>10.4f} {metrics['rmse']:>10.4f} "
                  f"{metrics['cv_mean']:>6.4f}±{metrics['cv_std']:.3f}{marker}")
        
        print("-"*80)
        print(f"★ Best model: {self.best_model_name}")
        print("="*80)


# =============================================================================
# VISUALIZATION
# =============================================================================

def plot_model_comparison(results, save_path='ml_model_comparison.png'):
    """
    Create bar chart comparing model performances.
    
    Parameters:
        results (dict): Model results from MCDMPredictor
        save_path (str): Path to save figure
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    models = list(results.keys())
    r2_scores = [results[m]['test_r2'] for m in models]
    mae_scores = [results[m]['mae'] for m in models]
    
    # R² comparison
    colors = ['#2ecc71' if r2 == max(r2_scores) else '#3498db' for r2 in r2_scores]
    bars1 = axes[0].bar(models, r2_scores, color=colors, edgecolor='white', linewidth=1.5)
    axes[0].set_title('Model Comparison: R² Score (higher is better)', fontweight='bold')
    axes[0].set_ylabel('R² Score')
    axes[0].set_ylim(0, 1)
    axes[0].axhline(y=0.8, color='red', linestyle='--', alpha=0.5, label='Good threshold (0.8)')
    axes[0].legend()
    
    # Add value labels
    for bar, val in zip(bars1, r2_scores):
        axes[0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                    f'{val:.3f}', ha='center', va='bottom', fontweight='bold')
    
    # MAE comparison
    colors = ['#2ecc71' if mae == min(mae_scores) else '#e74c3c' for mae in mae_scores]
    bars2 = axes[1].bar(models, mae_scores, color=colors, edgecolor='white', linewidth=1.5)
    axes[1].set_title('Model Comparison: MAE (lower is better)', fontweight='bold')
    axes[1].set_ylabel('Mean Absolute Error')
    
    # Add value labels
    for bar, val in zip(bars2, mae_scores):
        axes[1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.002,
                    f'{val:.4f}', ha='center', va='bottom', fontweight='bold')
    
    # Rotate x labels
    for ax in axes:
        ax.tick_params(axis='x', rotation=15)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"Saved: {save_path}")


def plot_feature_importance(importance_df, model_name, save_path='ml_feature_importance.png'):
    """
    Create horizontal bar chart of feature importance.
    
    Parameters:
        importance_df (pd.DataFrame): Feature importance data
        model_name (str): Name of the model
        save_path (str): Path to save figure
    """
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Take top 15 features
    top_features = importance_df.head(15)
    
    # Create color gradient
    colors = plt.cm.RdYlGn(np.linspace(0.2, 0.8, len(top_features)))[::-1]
    
    # Plot
    bars = ax.barh(range(len(top_features)), top_features['Importance_Pct'], 
                   color=colors, edgecolor='white', linewidth=1)
    
    ax.set_yticks(range(len(top_features)))
    ax.set_yticklabels(top_features['Feature'])
    ax.invert_yaxis()
    
    ax.set_xlabel('Importance (%)')
    ax.set_title(f'Feature Importance Analysis ({model_name})\nWhich factors most influence TOPSIS score?',
                 fontweight='bold', fontsize=13)
    
    # Add percentage labels
    for i, (bar, pct) in enumerate(zip(bars, top_features['Importance_Pct'])):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                f'{pct:.1f}%', ha='left', va='center', fontweight='bold')
    
    # Add annotation
    ax.annotate('Primary MCDM criteria', xy=(0.02, 0.98), xycoords='axes fraction',
                fontsize=9, style='italic', color='gray', va='top')
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"Saved: {save_path}")


def plot_prediction_scatter(y_true, y_pred, model_name, r2, save_path='ml_prediction_scatter.png'):
    """
    Create scatter plot of actual vs predicted values.
    
    Parameters:
        y_true (np.array): Actual TOPSIS scores
        y_pred (np.array): Predicted TOPSIS scores
        model_name (str): Name of the model
        r2 (float): R² score
        save_path (str): Path to save figure
    """
    fig, ax = plt.subplots(figsize=(8, 8))
    
    # Scatter plot
    ax.scatter(y_true, y_pred, alpha=0.6, c='#3498db', edgecolors='white', 
               linewidth=0.5, s=60)
    
    # Perfect prediction line
    min_val = min(y_true.min(), y_pred.min())
    max_val = max(y_true.max(), y_pred.max())
    ax.plot([min_val, max_val], [min_val, max_val], 'r--', linewidth=2, 
            label='Perfect prediction')
    
    ax.set_xlabel('Actual TOPSIS Score', fontsize=12)
    ax.set_ylabel('Predicted TOPSIS Score', fontsize=12)
    ax.set_title(f'Actual vs Predicted TOPSIS Scores\n{model_name} (R² = {r2:.4f})',
                 fontweight='bold', fontsize=13)
    ax.legend(loc='lower right')
    
    # Add R² annotation
    ax.annotate(f'R² = {r2:.4f}', xy=(0.05, 0.95), xycoords='axes fraction',
                fontsize=14, fontweight='bold', 
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    ax.set_xlim(min_val - 0.05, max_val + 0.05)
    ax.set_ylim(min_val - 0.05, max_val + 0.05)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"Saved: {save_path}")


def plot_residuals(y_true, y_pred, model_name, save_path='ml_residuals.png'):
    """
    Create residual analysis plot.
    
    Parameters:
        y_true (np.array): Actual values
        y_pred (np.array): Predicted values
        model_name (str): Model name
        save_path (str): Path to save figure
    """
    residuals = y_true - y_pred
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Residuals vs Predicted
    axes[0].scatter(y_pred, residuals, alpha=0.6, c='#9b59b6', edgecolors='white')
    axes[0].axhline(y=0, color='red', linestyle='--', linewidth=2)
    axes[0].set_xlabel('Predicted TOPSIS Score')
    axes[0].set_ylabel('Residuals')
    axes[0].set_title(f'Residuals vs Predicted ({model_name})', fontweight='bold')
    axes[0].grid(True, alpha=0.3)
    
    # Residual distribution
    axes[1].hist(residuals, bins=20, color='#9b59b6', edgecolor='white', alpha=0.7)
    axes[1].axvline(x=0, color='red', linestyle='--', linewidth=2)
    axes[1].set_xlabel('Residual Value')
    axes[1].set_ylabel('Frequency')
    axes[1].set_title('Residual Distribution', fontweight='bold')
    
    # Add statistics
    stats_text = f'Mean: {residuals.mean():.4f}\nStd: {residuals.std():.4f}'
    axes[1].annotate(stats_text, xy=(0.95, 0.95), xycoords='axes fraction',
                     fontsize=11, ha='right', va='top',
                     bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"Saved: {save_path}")


def create_combined_ml_report(predictor, importance_df, save_path='ml_analysis_report.png'):
    """
    Create comprehensive ML analysis report figure.
    
    Parameters:
        predictor (MCDMPredictor): Trained predictor object
        importance_df (pd.DataFrame): Feature importance data
        save_path (str): Path to save figure
    """
    fig = plt.figure(figsize=(16, 12))
    
    # Create grid
    gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)
    
    # 1. Model Comparison (top-left)
    ax1 = fig.add_subplot(gs[0, 0])
    models = list(predictor.results.keys())
    r2_scores = [predictor.results[m]['test_r2'] for m in models]
    colors = ['#2ecc71' if m == predictor.best_model_name else '#3498db' for m in models]
    bars = ax1.bar(models, r2_scores, color=colors, edgecolor='white')
    ax1.set_title('Model Comparison (R² Score)', fontweight='bold', fontsize=12)
    ax1.set_ylabel('R² Score')
    ax1.set_ylim(0, 1)
    ax1.tick_params(axis='x', rotation=20)
    for bar, val in zip(bars, r2_scores):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f'{val:.3f}', ha='center', fontsize=9, fontweight='bold')
    
    # 2. Feature Importance (top-right)
    ax2 = fig.add_subplot(gs[0, 1])
    top_10 = importance_df.head(10)
    colors = plt.cm.RdYlGn(np.linspace(0.2, 0.8, len(top_10)))[::-1]
    bars = ax2.barh(range(len(top_10)), top_10['Importance_Pct'], color=colors)
    ax2.set_yticks(range(len(top_10)))
    ax2.set_yticklabels(top_10['Feature'], fontsize=9)
    ax2.invert_yaxis()
    ax2.set_xlabel('Importance (%)')
    ax2.set_title(f'Top 10 Features ({predictor.best_model_name})', fontweight='bold', fontsize=12)
    
    # 3. Prediction Scatter (bottom-left)
    ax3 = fig.add_subplot(gs[1, 0])
    best_results = predictor.results[predictor.best_model_name]
    ax3.scatter(predictor.y_test, best_results['predictions'], 
                alpha=0.6, c='#3498db', edgecolors='white', s=50)
    min_val = min(predictor.y_test.min(), best_results['predictions'].min())
    max_val = max(predictor.y_test.max(), best_results['predictions'].max())
    ax3.plot([min_val, max_val], [min_val, max_val], 'r--', linewidth=2)
    ax3.set_xlabel('Actual TOPSIS Score')
    ax3.set_ylabel('Predicted TOPSIS Score')
    ax3.set_title(f'Actual vs Predicted (R² = {best_results["test_r2"]:.4f})', 
                  fontweight='bold', fontsize=12)
    ax3.set_aspect('equal')
    ax3.grid(True, alpha=0.3)
    
    # 4. Metrics Table (bottom-right)
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.axis('off')
    
    # Create table data
    table_data = []
    for name, metrics in predictor.results.items():
        table_data.append([
            name,
            f"{metrics['test_r2']:.4f}",
            f"{metrics['mae']:.4f}",
            f"{metrics['rmse']:.4f}",
            f"{metrics['cv_mean']:.3f}±{metrics['cv_std']:.3f}"
        ])
    
    table = ax4.table(cellText=table_data,
                      colLabels=['Model', 'R²', 'MAE', 'RMSE', 'CV Score'],
                      loc='center',
                      cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.8)
    
    # Highlight best model row
    best_idx = list(predictor.results.keys()).index(predictor.best_model_name)
    for j in range(5):
        table[(best_idx + 1, j)].set_facecolor('#d5f5e3')
    
    ax4.set_title('Performance Metrics Summary', fontweight='bold', fontsize=12, y=0.95)
    
    # Main title
    fig.suptitle('Machine Learning Analysis Report\nMCDM + ML Hybrid Approach for GitHub Project Success Prediction',
                 fontsize=14, fontweight='bold', y=0.98)
    
    plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"Saved: {save_path}")


# =============================================================================
# LATEX EXPORT
# =============================================================================

def export_ml_results_latex(predictor, importance_df, filename='latex_ml_results.tex'):
    """
    Export ML results to LaTeX format.
    
    Parameters:
        predictor (MCDMPredictor): Trained predictor
        importance_df (pd.DataFrame): Feature importance
        filename (str): Output filename
    """
    with open(filename, 'w', encoding='utf-8') as f:
        # Model comparison table
        f.write("% ML Model Comparison Table\n")
        f.write("\\begin{table}[htbp]\n")
        f.write("\\centering\n")
        f.write("\\caption{Makine Öğrenme Model Performans Karşılaştırması}\n")
        f.write("\\label{tab:ml_comparison}\n")
        f.write("\\begin{tabular}{lcccc}\n")
        f.write("\\toprule\n")
        f.write("Model & $R^2$ & MAE & RMSE & CV Score \\\\\n")
        f.write("\\midrule\n")
        
        for name, metrics in predictor.results.items():
            marker = " $\\star$" if name == predictor.best_model_name else ""
            f.write(f"{name}{marker} & {metrics['test_r2']:.4f} & {metrics['mae']:.4f} & "
                   f"{metrics['rmse']:.4f} & {metrics['cv_mean']:.3f}$\\pm${metrics['cv_std']:.3f} \\\\\n")
        
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")
        f.write("\\end{table}\n\n")
        
        # Feature importance table
        f.write("% Feature Importance Table\n")
        f.write("\\begin{table}[htbp]\n")
        f.write("\\centering\n")
        f.write("\\caption{Özellik Önem Sıralaması (Random Forest)}\n")
        f.write("\\label{tab:feature_importance}\n")
        f.write("\\begin{tabular}{clc}\n")
        f.write("\\toprule\n")
        f.write("Sıra & Özellik & Önem (\\%) \\\\\n")
        f.write("\\midrule\n")
        
        for i, (_, row) in enumerate(importance_df.head(10).iterrows(), 1):
            f.write(f"{i} & {row['Feature']} & {row['Importance_Pct']:.2f} \\\\\n")
        
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")
        f.write("\\end{table}\n")
    
    print(f"Saved: {filename}")


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main execution function."""
    print("="*70)
    print("MCDM + ML HYBRID ANALYSIS")
    print("GitHub Open Source Project Success Prediction")
    print("="*70)
    
    # Step 1: Load data
    print("\n[1/6] Loading data from database...")
    df = load_data()
    
    # Step 2: Calculate TOPSIS scores (target variable)
    print("\n[2/6] Calculating TOPSIS scores...")
    topsis_scores = calculate_topsis_scores(df)
    df['topsis_score'] = topsis_scores
    print(f"TOPSIS scores calculated for {len(topsis_scores)} repositories")
    print(f"Score range: {topsis_scores.min():.4f} - {topsis_scores.max():.4f}")
    
    # Step 3: Prepare features
    print("\n[3/6] Preparing features...")
    X, feature_names = prepare_features(df)
    y = df['topsis_score'].values
    
    # Step 4: Train models
    print("\n[4/6] Training ML models...")
    predictor = MCDMPredictor()
    predictor.train(X.values, y, feature_names)
    
    # Step 5: Feature importance
    print("\n[5/6] Analyzing feature importance...")
    importance_df = predictor.get_feature_importance()
    print("\nTop 10 Most Important Features:")
    print(importance_df.head(10).to_string(index=False))
    
    # Step 6: Generate outputs
    print("\n[6/6] Generating visualizations and reports...")
    
    # Print summary
    predictor.print_results_summary()
    
    # Create visualizations
    plot_model_comparison(predictor.results)
    plot_feature_importance(importance_df, predictor.best_model_name)
    
    best_results = predictor.results[predictor.best_model_name]
    plot_prediction_scatter(predictor.y_test, best_results['predictions'],
                           predictor.best_model_name, best_results['test_r2'])
    plot_residuals(predictor.y_test, best_results['predictions'], predictor.best_model_name)
    
    create_combined_ml_report(predictor, importance_df)
    
    # Export LaTeX
    export_ml_results_latex(predictor, importance_df)
    
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE!")
    print("="*70)
    print("\nGenerated files:")
    print("  - ml_model_comparison.png")
    print("  - ml_feature_importance.png")
    print("  - ml_prediction_scatter.png")
    print("  - ml_residuals.png")
    print("  - ml_analysis_report.png")
    print("  - latex_ml_results.tex")
    
    return predictor, importance_df, df


if __name__ == "__main__":
    predictor, importance_df, df = main()











