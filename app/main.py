import datetime
import tempfile
import numpy as np
import matplotlib.pyplot as plt
import japanize_matplotlib
from google.cloud import storage
from flask import jsonify, request, make_response

# Google Cloud Storageクライアントの初期化
storage_client = storage.Client()
bucket_name = 'assets_image_bucket'


# 署名付きURLの生成
def generate_signed_url(bucket_name, blob_name, expiration=3600):
    """Generates a signed URL for a blob."""
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    url = blob.generate_signed_url(expiration=datetime.timedelta(seconds=expiration))
    return url


# パブリックURLの生成
def generate_public_url(bucket_name, blob_name):
    """Generates a public URL for a blob."""
    return f"https://storage.googleapis.com/{bucket_name}/{blob_name}"


# Cloud Storageにアップロード
def upload_to_bucket(blob_name, path_to_file):
    """Upload data to a bucket"""
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(path_to_file)
    return blob_name


# 金額をフォーマット
def format_amount(amount):
    if amount >= 10000:
        return f"{int(amount // 10000)}億{int(amount % 10000)}万円"
    else:
        return f"{int(amount)}万円"


# グラフを生成する関数
def generate_plot(pension_income, shortfall, savings, years, filename):
    """老後生活費の貯金・年金・不足分の積み上げ棒グラフを作成
    """
    fig, ax = plt.subplots()

    # 積み上げ棒グラフの生成
    ax.bar(years, pension_income, label='年金収入', color='green')
    # 不足分を貯金から補える場合と補えない場合の棒グラフの生成
    for i in range(len(years)):
        if savings[i] > 0:
            if savings[i] > shortfall[i]:
                ax.bar(years[i], shortfall[i], bottom=pension_income[i], label='貯金切り崩し', color='blue')
            else:
                ax.bar(years[i], savings[i], bottom=pension_income[i], label='貯金切り崩し', color='blue')
                ax.bar(years[i], shortfall[i] - savings[i], bottom=pension_income[i] + savings[i], label='資金不足分', color='red')
        else:
            ax.bar(years[i], shortfall[i], bottom=pension_income[i], label='資金不足分', color='red')
    # ラベルとタイトル
    ax.set_xlabel('年齢')
    ax.set_ylabel('金額（万円）')
    plt.title('老後の生活費（貯金・年金収入・不足分の推移）')
    # 凡例
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys())

    # 一時ファイルに画像を保存
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
        plt.savefig(tmpfile.name)
        tmpfile_path = tmpfile.name
    plt.close(fig)
    return tmpfile_path


# Cloud Functionのエントリーポイント
def calculate(request):
    # CORS対応: OPTIONSリクエストに対してCORSヘッダーを返す
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    # フォームデータの取得
    data = request.form
    current_age = int(data['current_age'])
    pension_start_age = int(data['pension_start_age'])
    expected_lifespan = int(data['expected_lifespan'])
    monthly_expenses = float(data['monthly_expenses'])
    current_savings = float(data['current_savings'])
    monthly_savings = float(data['monthly_savings'])
    growth_rate = float(data['growth_rate'])
    slide_rate = float(data['slide_rate'])
    monthly_pension = float(data['monthly_pension'])

    # 経過年数に伴い更新される変数
    latest_monthly_savings = monthly_savings
    latest_current_savings = current_savings
    latest_monthly_expenses = monthly_expenses
    latest_monthly_pension = monthly_pension

    # 変数の初期化
    years = np.arange(pension_start_age, expected_lifespan + 1)
    living_expenses = np.zeros_like(years, dtype=float)
    pension_income = np.zeros_like(years, dtype=float)
    shortfall = np.zeros_like(years, dtype=float)
    savings = np.zeros_like(years, dtype=float)

    # 物価上昇率を考慮した生活費と年金額
    working_years = pension_start_age - current_age
    retirement_years = expected_lifespan - pension_start_age
    for year in range(working_years):
        latest_monthly_savings += latest_monthly_savings * growth_rate / 100
        latest_current_savings += latest_monthly_savings * 12
        latest_monthly_expenses += latest_monthly_expenses * growth_rate / 100
        latest_monthly_pension += latest_monthly_pension * slide_rate / 100

    # 年金受給開始後の計算
    total_expenses_after_retirement = 0
    total_pension = 0
    savings[0] = latest_current_savings
    for year in range(retirement_years + 1):
        latest_monthly_expenses += latest_monthly_expenses * growth_rate / 100
        total_expenses_after_retirement += latest_monthly_expenses * 12
        latest_monthly_pension += latest_monthly_pension * slide_rate / 100
        total_pension += latest_monthly_pension * 12
        living_expenses[year] = latest_monthly_expenses * 12
        pension_income[year] = latest_monthly_pension * 12
        shortfall[year] = max(0, living_expenses[year] - pension_income[year])
        savings[year] = savings[year - 1] - shortfall[year] if year > 0 else latest_current_savings - shortfall[year]

    # 必要な老後資金
    total_funds_needed = total_expenses_after_retirement - total_pension
    total_lack_funds = total_funds_needed - latest_current_savings

    # 計算結果のフォーマット
    total_expenses_after_retirement = format_amount(total_expenses_after_retirement)
    total_pension = format_amount(total_pension)
    total_funds_needed = format_amount(total_funds_needed)
    latest_current_savings = format_amount(latest_current_savings)
    total_lack_funds = format_amount(total_lack_funds)

    # グラフの生成とアップロード
    plot_filename = f"plot_{current_age}_{pension_start_age}_{expected_lifespan}.png"
    plot_filepath = generate_plot(pension_income, shortfall, savings, years, plot_filename)
    upload_to_bucket(plot_filename, plot_filepath)
    plot_url = generate_public_url(bucket_name, plot_filename)

    # 計算結果をJSONで返却
    response = jsonify({
        "plot_url": plot_url,
        "total_expenses_after_retirement": total_expenses_after_retirement,
        "total_pension": total_pension,
        "total_funds_needed": total_funds_needed,
        "latest_current_savings": latest_current_savings,
        "total_lack_funds": total_lack_funds
    })
    response.headers['Access-Control-Allow-Origin'] = '*'  # クライアントからのアクセスを許可
    return response
