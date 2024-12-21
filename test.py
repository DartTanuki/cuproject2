import plotly.express as px

# using the iris dataset
df = px.data.iris()
print(df)
# plotting the scatter chart
# fig = px.scatter(df, x="species", y="petal_width")
#
# # showing the plot
# fig.show()