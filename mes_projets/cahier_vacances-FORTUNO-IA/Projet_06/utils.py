import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf


def mae(y_vrai, y_prevu):
    """Mean Absolute Error: the average gap, in ice creams, between reality and forecast.

    Arguments:
    y_vrai -- array of observed sales
    y_prevu -- array of predicted sales, same length

    Returns:
    score -- the mean absolute error
    """
    return float(np.mean(np.abs(np.asarray(y_vrai) - np.asarray(y_prevu))))


def prevision_1_jour(resultat, serie, n_test):
    """Predict each of the last n_test days, one day ahead, without re-estimating the model.

    Every evening the model looks at everything observed so far and predicts tomorrow. The
    coefficients are the ones learned on the training set: only the observations move forward.

    Arguments:
    resultat -- a fitted statsmodels ARIMA result
    serie -- the complete sales series (training period + test period)
    n_test -- number of days at the end of the series to predict

    Returns:
    previsions -- array of n_test one-day-ahead predictions
    """
    applique = resultat.apply(np.asarray(serie, dtype=float))
    return applique.get_prediction(start=len(serie) - n_test).predicted_mean


def tableau_des_scores(scores):
    """Sort a dict of {model name: MAE} into a readable DataFrame, best model first.

    Arguments:
    scores -- dict mapping a model name to its MAE

    Returns:
    tableau -- DataFrame with columns "modèle" and "erreur moyenne (glaces/jour)"
    """
    tableau = pd.DataFrame({"modèle": list(scores), "erreur moyenne (glaces/jour)": list(scores.values())})
    return tableau.sort_values("erreur moyenne (glaces/jour)").round(2).reset_index(drop=True)


def plot_ventes(df, titre="Ventes quotidiennes de glaces"):
    """Plot the daily sales, one color per season.

    Arguments:
    df -- DataFrame with columns date, saison and ventes
    titre -- title of the figure
    """
    plt.figure(figsize=(13, 4))
    for saison, groupe in df.groupby("saison"):
        plt.plot(groupe["date"], groupe["ventes"], linewidth=1, label=f"été {saison}")
    plt.axhline(df["ventes"].mean(), color="black", linestyle="--", linewidth=1,
                label=f"moyenne ({df['ventes'].mean():.0f})")
    plt.ylabel("Glaces vendues")
    plt.title(titre)
    plt.legend(ncol=5, fontsize=8)
    plt.tight_layout()
    plt.show()


def plot_correlogrammes(serie, lags=15, titre=""):
    """Draw the ACF and the PACF of a series side by side.

    The blue band is the zone where a bar is indistinguishable from zero: only the bars
    sticking out of it carry real information.

    Arguments:
    serie -- the time series, as an array
    lags -- number of lags to display
    titre -- extra text added to both titles
    """
    fig, axes = plt.subplots(1, 2, figsize=(13, 4))
    plot_acf(np.asarray(serie, dtype=float), lags=lags, ax=axes[0])
    axes[0].set_title(f"ACF {titre}".strip())
    plot_pacf(np.asarray(serie, dtype=float), lags=lags, ax=axes[1], method="ywm")
    axes[1].set_title(f"PACF {titre}".strip())
    for ax in axes:
        ax.set_xlabel("Retard (jours)")
    plt.tight_layout()
    plt.show()


def plot_previsions(dates, reel, previsions, titre="Prévision à 1 jour"):
    """Plot the real sales of the test period against one or several models.

    Arguments:
    dates -- dates of the test period
    reel -- observed sales over that period
    previsions -- dict mapping a model name to its array of predictions
    titre -- title of the figure
    """
    plt.figure(figsize=(13, 4.5))
    plt.plot(dates, reel, color="black", marker="o", markersize=4, linewidth=2, label="ventes réelles")
    for nom, valeurs in previsions.items():
        plt.plot(dates, valeurs, marker=".", linewidth=1.2, alpha=0.9, label=nom)
    plt.ylabel("Glaces vendues")
    plt.title(titre)
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.show()


def plot_semaine(historique, resultat, steps=7, jours_affiches=40, titre="La semaine du glacier"):
    """Plot the last observed days, then the forecast for the coming days with its confidence band.

    Arguments:
    historique -- the observed series used to fit the model
    resultat -- a fitted statsmodels ARIMA result
    steps -- number of days to forecast
    jours_affiches -- number of past days to show before the forecast
    titre -- title of the figure
    """
    historique = np.asarray(historique, dtype=float)
    forecast = resultat.get_forecast(steps=steps)
    moyenne = np.asarray(forecast.predicted_mean, dtype=float)
    intervalle = np.asarray(forecast.conf_int(), dtype=float)

    passe = np.arange(-jours_affiches, 0)
    futur = np.arange(1, steps + 1)

    plt.figure(figsize=(11, 4.5))
    plt.plot(passe, historique[-jours_affiches:], color="black", linewidth=1.5, label="ventes observées")
    plt.plot(futur, moyenne, color="crimson", marker="o", linewidth=2, label="prévision")
    plt.fill_between(futur, intervalle[:, 0], intervalle[:, 1], color="crimson", alpha=0.15,
                     label="intervalle de confiance 95 %")
    plt.axhline(historique.mean(), color="grey", linestyle="--", linewidth=1, label="moyenne historique")
    plt.axvline(0, color="grey", linewidth=0.8)
    plt.xlabel("Jours (0 = aujourd'hui)")
    plt.ylabel("Glaces vendues")
    plt.title(titre)
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.show()
