import pandas as pd

# Define the sample data for Semester III
data = [
    {
        "PRN": "SOE2022B0308075", "Name": "VARVATE ABHAY DHONDIBHA", "Division": "A",
        "UDSBS301_Assignment": 4, "UDSBS301_Attendance": 5, "UDSBS301_UT": 14, "UDSBS301_MSE": 18,
        "UDSPC302_Assignment": 3, "UDSPC302_Attendance": 4, "UDSPC302_UT": 15, "UDSPC302_MSE": 19,
        "UDSPC303_Assignment": 5, "UDSPC303_Attendance": 5, "UDSPC303_UT": 18, "UDSPC303_MSE": 17,
        "UDSPC304_Assignment": 2, "UDSPC304_Attendance": 3, "UDSPC304_UT": 12, "UDSPC304_MSE": 18
    },
    {
        "PRN": "SOE24BTAM28", "Name": "Adsul Shravan Balaji", "Division": "B",
        "UDSBS301_Assignment": 5, "UDSBS301_Attendance": 4, "UDSBS301_UT": 18, "UDSBS301_MSE": 11,
        "UDSPC302_Assignment": 4, "UDSPC302_Attendance": 3, "UDSPC302_UT": 14, "UDSPC302_MSE": 11,
        "UDSPC303_Assignment": 5, "UDSPC303_Attendance": 5, "UDSPC303_UT": 16, "UDSPC303_MSE": 15,
        "UDSPC304_Assignment": 4, "UDSPC304_Attendance": 5, "UDSPC304_UT": 15, "UDSPC304_MSE": 14
    }
]

df = pd.DataFrame(data)
df.to_excel('sample_results.xlsx', index=False)
print("sample_results.xlsx generated successfully.")
