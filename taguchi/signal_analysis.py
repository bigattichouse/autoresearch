"""
Signal-to-Noise Ratio (SNR) Analysis for Taguchi Experiments

This module provides signal analysis capabilities to help users understand
factor importance and guide future experimental design decisions.
"""

import numpy as np
from typing import Dict, List, Any, Tuple, Optional
import math


class SignalAnalyzer:
    """
    Analyzes experimental results to compute SNR values and factor importance.
    
    In Taguchi methodology, the Signal-to-Noise Ratio (SNR) helps identify
    factors that have consistent effects vs. those that introduce noise.
    Higher SNR indicates more consistent, controllable factors.
    """
    
    def __init__(self):
        self.results: Dict[int, float] = {}
        self.factors: Dict[str, List[str]] = {}
        self.runs: List[Dict] = []
        
    def set_experimental_data(self, runs: List[Dict], results: Dict[int, float], factors: Dict[str, List[str]]):
        """Set experimental data for analysis."""
        self.runs = runs
        self.results = results
        self.factors = factors
        
    def calculate_snr_by_factor(self, higher_is_better: bool = False) -> Dict[str, Dict[str, float]]:
        """
        Calculate Signal-to-Noise Ratio for each factor level.
        
        Args:
            higher_is_better: If True, use "larger is better" SNR formula.
                             If False, use "smaller is better" SNR formula.
        
        Returns:
            Dict mapping factor_name -> {level: snr_value}
        """
        snr_by_factor = {}
        
        for factor_name in self.factors.keys():
            snr_by_factor[factor_name] = {}
            
            # Group results by factor level
            level_results = {}
            for run in self.runs:
                if run['run_id'] in self.results:
                    level = run['factors'][factor_name]
                    if level not in level_results:
                        level_results[level] = []
                    level_results[level].append(self.results[run['run_id']])
            
            # Calculate SNR for each level
            for level, values in level_results.items():
                if len(values) > 0:
                    snr = self._calculate_snr(values, higher_is_better)
                    snr_by_factor[factor_name][level] = snr
                    
        return snr_by_factor
    
    def _calculate_snr(self, values: List[float], higher_is_better: bool) -> float:
        """
        Calculate SNR for a set of values.
        
        Taguchi SNR formulas:
        - Smaller is better: SNR = -10 * log10(mean(y^2))
        - Larger is better: SNR = -10 * log10(mean(1/y^2))
        """
        if not values:
            return 0.0
            
        values = np.array(values)
        
        if higher_is_better:
            # Larger is better
            # Avoid division by zero
            safe_values = np.maximum(values, 1e-10)
            mean_inverse_squares = np.mean(1.0 / (safe_values ** 2))
            snr = -10 * math.log10(mean_inverse_squares) if mean_inverse_squares > 0 else 0
        else:
            # Smaller is better (most common for loss functions)
            mean_squares = np.mean(values ** 2)
            snr = -10 * math.log10(mean_squares) if mean_squares > 0 else 0
            
        return snr
    
    def calculate_factor_effects(self) -> Dict[str, Dict[str, Any]]:
        """
        Calculate factor effects including means, ranges, and SNR.
        
        Returns comprehensive analysis for each factor.
        """
        factor_effects = {}
        
        for factor_name in self.factors.keys():
            # Group results by factor level
            level_data = {}
            for run in self.runs:
                if run['run_id'] in self.results:
                    level = run['factors'][factor_name]
                    if level not in level_data:
                        level_data[level] = []
                    level_data[level].append(self.results[run['run_id']])
            
            # Calculate statistics for each level
            level_stats = {}
            for level, values in level_data.items():
                if values:
                    level_stats[level] = {
                        'mean': np.mean(values),
                        'std': np.std(values),
                        'count': len(values),
                        'values': values
                    }
            
            if level_stats:
                # Calculate overall factor effect
                means = [stats['mean'] for stats in level_stats.values()]
                factor_range = max(means) - min(means)
                
                factor_effects[factor_name] = {
                    'level_means': {level: stats['mean'] for level, stats in level_stats.items()},
                    'level_stds': {level: stats['std'] for level, stats in level_stats.items()},
                    'range': factor_range,
                    'level_stats': level_stats
                }
                
        return factor_effects
    
    def rank_factors_by_importance(self, snr_data: Dict[str, Dict[str, float]] = None) -> List[Tuple[str, float]]:
        """
        Rank factors by importance using SNR range.
        
        Args:
            snr_data: Precomputed SNR data, or None to compute fresh
            
        Returns:
            List of (factor_name, importance_score) tuples, sorted by importance
        """
        if snr_data is None:
            snr_data = self.calculate_snr_by_factor()
            
        factor_importance = []
        
        for factor_name, level_snrs in snr_data.items():
            if level_snrs:
                snr_values = list(level_snrs.values())
                snr_range = max(snr_values) - min(snr_values)
                factor_importance.append((factor_name, snr_range))
        
        # Sort by importance (higher SNR range = more important)
        factor_importance.sort(key=lambda x: x[1], reverse=True)
        return factor_importance
    
    def generate_signal_report(self, higher_is_better: bool = False) -> str:
        """
        Generate a comprehensive signal analysis report.
        
        Returns formatted text report with SNR analysis and recommendations.
        """
        if not self.results or not self.runs:
            return "No experimental data available for signal analysis."
        
        # Calculate SNR and factor effects
        snr_data = self.calculate_snr_by_factor(higher_is_better)
        factor_effects = self.calculate_factor_effects()
        factor_rankings = self.rank_factors_by_importance(snr_data)
        
        # Build report
        lines = []
        lines.append("=" * 70)
        lines.append("TAGUCHI SIGNAL-TO-NOISE RATIO (SNR) ANALYSIS")
        lines.append("=" * 70)
        lines.append("")
        
        # Summary
        lines.append("📊 EXPERIMENT SUMMARY:")
        lines.append(f"   Total runs: {len(self.runs)}")
        lines.append(f"   Successful runs: {len(self.results)}")
        lines.append(f"   Factors analyzed: {len(self.factors)}")
        lines.append(f"   Optimization goal: {'Maximize' if higher_is_better else 'Minimize'} metric")
        lines.append("")
        
        # Factor Importance Ranking
        lines.append("🎯 FACTOR IMPORTANCE RANKING:")
        lines.append("   (Based on SNR range - higher = more important)")
        lines.append("   " + "-" * 50)
        
        for i, (factor, importance) in enumerate(factor_rankings, 1):
            lines.append(f"   {i:2}. {factor:20s} SNR Range: {importance:8.3f} dB")
        lines.append("")
        
        # Detailed SNR Analysis
        lines.append("🔍 DETAILED SNR ANALYSIS BY FACTOR:")
        lines.append("   " + "-" * 50)
        
        for factor_name in self.factors.keys():
            lines.append(f"\n   📈 {factor_name}:")
            
            if factor_name in snr_data and snr_data[factor_name]:
                level_snrs = snr_data[factor_name]
                factor_effect = factor_effects.get(factor_name, {})
                
                # SNR values by level
                for level, snr in level_snrs.items():
                    mean = factor_effect.get('level_means', {}).get(level, 0)
                    std = factor_effect.get('level_stds', {}).get(level, 0)
                    count = factor_effect.get('level_stats', {}).get(level, {}).get('count', 0)
                    
                    lines.append(f"      {level:10s}: SNR={snr:8.3f} dB, Mean={mean:8.4f}, Std={std:6.4f}, n={count}")
                
                # Factor insights
                snr_values = list(level_snrs.values())
                best_snr_level = max(level_snrs.keys(), key=lambda k: level_snrs[k])
                worst_snr_level = min(level_snrs.keys(), key=lambda k: level_snrs[k])
                snr_range = max(snr_values) - min(snr_values)
                
                lines.append(f"      → SNR Range: {snr_range:.3f} dB")
                lines.append(f"      → Most consistent: {best_snr_level} ({level_snrs[best_snr_level]:.3f} dB)")
                lines.append(f"      → Least consistent: {worst_snr_level} ({level_snrs[worst_snr_level]:.3f} dB)")
                
        lines.append("")
        
        # Recommendations
        lines.append("💡 RECOMMENDATIONS:")
        lines.append("   " + "-" * 30)
        
        if factor_rankings:
            # Most important factors
            top_factors = factor_rankings[:3]
            lines.append("   🎯 Focus on these high-impact factors:")
            for factor, importance in top_factors:
                if importance > 1.0:  # Significant SNR range
                    lines.append(f"      • {factor}: Strong signal (SNR range: {importance:.3f} dB)")
                else:
                    lines.append(f"      • {factor}: Moderate signal (SNR range: {importance:.3f} dB)")
            
            lines.append("")
            
            # Low-impact factors
            low_impact = [(f, i) for f, i in factor_rankings if i < 0.5]
            if low_impact:
                lines.append("   ⚠️  Consider removing low-impact factors:")
                for factor, importance in low_impact:
                    lines.append(f"      • {factor}: Weak signal (SNR range: {importance:.3f} dB)")
                lines.append("      → These factors may not significantly affect your metric")
                lines.append("")
            
            # Optimal settings recommendation  
            lines.append("   🎯 Recommended factor settings (based on SNR):")
            for factor_name, level_snrs in snr_data.items():
                if level_snrs:
                    best_level = max(level_snrs.keys(), key=lambda k: level_snrs[k])
                    best_snr = level_snrs[best_level]
                    lines.append(f"      • {factor_name}: {best_level} (SNR: {best_snr:.3f} dB)")
        
        lines.append("")
        lines.append("📚 UNDERSTANDING SNR VALUES:")
        lines.append("   • Higher SNR = More consistent, controllable factor")
        lines.append("   • SNR Range > 3 dB = Significant factor effect")
        lines.append("   • SNR Range < 1 dB = Weak factor effect")
        lines.append("   • Focus future experiments on high-SNR factors")
        lines.append("")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def suggest_next_experiments(self, current_snr_data: Dict[str, Dict[str, float]] = None) -> Dict[str, Any]:
        """
        Suggest next experiments based on SNR analysis.
        
        Returns suggestions for refining factor ranges or adding new factors.
        """
        if current_snr_data is None:
            current_snr_data = self.calculate_snr_by_factor()
            
        factor_rankings = self.rank_factors_by_importance(current_snr_data)
        
        suggestions = {
            'high_priority_factors': [],
            'refinement_candidates': [],
            'elimination_candidates': [],
            'new_factor_suggestions': []
        }
        
        for factor, importance in factor_rankings:
            if importance > 3.0:  # Very significant
                suggestions['high_priority_factors'].append({
                    'factor': factor,
                    'importance': importance,
                    'action': 'Explore more levels around optimal settings'
                })
            elif importance > 1.0:  # Moderately significant
                suggestions['refinement_candidates'].append({
                    'factor': factor,
                    'importance': importance, 
                    'action': 'Refine range around best performing levels'
                })
            elif importance < 0.5:  # Low significance
                suggestions['elimination_candidates'].append({
                    'factor': factor,
                    'importance': importance,
                    'action': 'Consider removing from future experiments'
                })
        
        # Suggest interaction studies for top factors
        if len(suggestions['high_priority_factors']) >= 2:
            top_factors = [f['factor'] for f in suggestions['high_priority_factors'][:2]]
            suggestions['interaction_studies'] = {
                'factors': top_factors,
                'action': f'Study interactions between {" and ".join(top_factors)}'
            }
            
        return suggestions